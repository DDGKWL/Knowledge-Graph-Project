from flask import Flask, jsonify, render_template, request
import json
import pandas as pd
import os
import networkx as nx
from openai import OpenAI
import httpx

from flask_cors import CORS
from part_compare import compare_parts_core, get_part_taxonomy

app = Flask(__name__)
CORS(app)  # 允许所有域名跨域



# -------------------------- RAG 新增依赖 --------------------------
from langchain.text_splitter import RecursiveCharacterTextSplitter  # 文本分块
from langchain_openai import OpenAIEmbeddings  # OpenAI 嵌入模型
from langchain_community.vectorstores import FAISS  # 轻量级向量数据库（本地存储，无需额外服务）
from langchain.docstore.document import Document  # LangChain 标准文档格式
# ------------------------------------------------------------------
# -------------------------- RAG 配置（新增） --------------------------
# 1. 向量存储路径（本地保存，避免重复构建）
VECTOR_STORE_PATH = os.path.join(os.path.dirname(__file__), "artifact_rag_vectorstore")
# 2. 嵌入模型（与 OpenAI 客户端配置一致，复用代理）
embeddings = OpenAIEmbeddings(
    openai_api_base="https://ssvip.dmxapi.com/v1",
    openai_api_key="sk-5aZQx8y8RzmPX4MHT79de0pnaK8grVJtT3CpgwmPAcYiGsrI"  # 复用原 API Key
    # openai_api_base="http://38.147.105.35:3030/v1",
    # openai_api_key="sk-ptH8ova7JyCVEzmd8pXT3CPUn5cOz2aub68b2kOlZdD20ElF"  # 复用原 API Key
)
# 3. 全局变量：存储 RAG 向量数据库
vector_store = None

RELATION_COLOR_MAP = {
    # 原有关系（保留）
    "饰有": "#FF6B6B", "材质为": "#4ECDC4", "制作工艺为": "#45B7D1",
    # 新增基础版关系（与前端颜色保持一致）
    "具有": "#FF6B6B", "被誉为": "#4ECDC4", "是": "#45B7D1",
    "形成了": "#96CEB4", "又称": "#FFEAA7", "在": "#DDA0DD",
    "需要": "#a0d792f7", "易干裂": "#87CEEB", "易霉变": "#98D8C8",
    "易虫蛀": "#FF8C94", "易损毁": "#C4A484", "难逃": "#E0E0E0",
    "存世": "#FFAAA5", "收藏了": "#FFD3B6", "加入": "#FFFFB8",
    "开展了": "#B5EAD7", "邀请": "#C7CEEA", "发行": "#F2D7EE",
    "推出": "#E2F0CB", "召开": "#FFCFD2", "举办": "#C5E3ED",
    "收录了": "#F7D794", "总结了": "#B8E986", "精心拍摄了": "#90CDF4",
    "展示了": "#E9D8FD"
}


def extract_kg_to_rag_documents():
    """
    从已构建的知识图谱（G、node_properties、node_relations）中提取文本，生成 RAG 文档列表
    返回：list[Document] - 每个元素对应1个文物的结构化信息文本
    """
    rag_documents = []
    # 1. 筛选所有文物节点（is_artifact=1）
    artifact_nodes = [
        node_id for node_id, props in node_properties.items()
        if props.get('is_artifact', 0) == 1
    ]

    for artifact_id in artifact_nodes:
        # 2. 获取当前文物的基础属性（原始名称、所属标识、断代等）
        art_props = node_properties[artifact_id]
        art_name = art_props.get('original_name', artifact_id)  # 文物名称（如“凤鸣”）
        art_belongs = art_props.get('belongs_to_clean', '')  # 所属标识（如“1”）
        art_basic_info = f"文物名称：{art_name}（唯一ID：{artifact_id}）\n" \
                         f"所属标识：{art_belongs}\n" \
                         f"基础属性：{art_props}\n"

        # 3. 获取当前文物的所有关联关系（直接关联的边）
        art_relations = []
        for u, v, edge_data in G.edges(artifact_id, data=True):
            # 区分“文物→其他节点”和“其他节点→文物”（统一表述为“文物 关系 目标节点”）
            if u == artifact_id:
                target_node = v
                relation = edge_data['relation']
                art_relations.append(f"- {art_name} {relation} {node_properties[target_node]['original_name']}")
            else:
                target_node = u
                relation = edge_data['relation']
                art_relations.append(f"- {node_properties[target_node]['original_name']} {relation} {art_name}")

        # 4. 获取当前文物的间接关联节点（两跳内非文物节点，补充上下文）
        _, two_hop_edges = get_same_belongs_to_data(artifact_id)  # 复用原有筛选函数
        indirect_relations = []
        for edge in two_hop_edges:
            if edge['source'] != artifact_id and edge['target'] != artifact_id:
                source_name = node_properties[edge['source']]['original_name']
                target_name = node_properties[edge['target']]['original_name']
                indirect_relations.append(f"- 间接关联：{source_name} {edge['relation']} {target_name}")

        # 5. 拼接当前文物的完整文本（用于向量化）
        full_text = art_basic_info + "\n" \
                                     "直接关联关系：\n" + "\n".join(art_relations) + "\n" \
                                                                                    "两跳内间接关联：\n" + "\n".join(
            indirect_relations)

        # 6. 生成 LangChain Document（添加元数据，便于后续追溯）
        doc = Document(
            page_content=full_text,
            metadata={
                "artifact_id": artifact_id,  # 文物唯一ID
                "artifact_name": art_name,  # 文物名称
                "belongs_to": art_belongs,  # 所属标识（用于筛选）
                "source": "knowledge_graph"  # 数据来源（区分其他文档）
            }
        )
        rag_documents.append(doc)

    print(f"从知识图谱提取 RAG 文档完成，共 {len(rag_documents)} 个文物文档")
    return rag_documents


def build_or_load_rag_vectorstore(force_rebuild=False):
    """
    构建或加载 RAG 向量知识库：
    - 若本地已存在向量库，直接加载；
    - 若不存在，从知识图谱提取文档并构建向量库。
    返回：FAISS 对象 - 可用于后续相似性检索
    """
    global vector_store
    # 新增：若强制重新构建，先删除旧向量库文件夹
    if force_rebuild and os.path.exists(VECTOR_STORE_PATH):
        print(f"[强制重新构建] 正在删除旧向量库：{VECTOR_STORE_PATH}")
        # 递归删除文件夹及内部所有文件
        import shutil
        shutil.rmtree(VECTOR_STORE_PATH)
        print(f"[强制重新构建] 旧向量库已删除")
    # 1. 检查本地向量库是否存在
    if os.path.exists(VECTOR_STORE_PATH):
        print(f"正在加载本地 RAG 向量库：{VECTOR_STORE_PATH}")
        vector_store = FAISS.load_local(
            folder_path=VECTOR_STORE_PATH,
            embeddings=embeddings,
            allow_dangerous_deserialization=True  # 本地文件可信，允许反序列化
        )
        print(f"向量库加载完成，共包含 {vector_store.index.ntotal} 个文档向量")
        # -------------------------- 兼容版：提取 Documents 的通用方法 --------------------------
        print("\n" + "=" * 80)
        print("【验证：RAG 向量库中的 Documents 内容】")
        try:
            # 方案1：优先尝试 get_all_documents()（适配新版本）
            all_docs = vector_store.get_all_documents()
        except AttributeError:
            # 方案2：旧版本兼容（通过 index_to_docstore_id + docstore 提取）
            all_docs = []
            # 1. 获取“索引→文档ID”的映射（vector_store.index_to_docstore_id 是字典）
            for idx in range(vector_store.index.ntotal):
                # 2. 通过索引获取文档ID
                doc_id = vector_store.index_to_docstore_id[idx]
                # 3. 通过文档ID从 docstore 中获取 Document 对象
                doc = vector_store.docstore.search(doc_id)
                if doc is not None:  # 避免空文档
                    all_docs.append(doc)

        # 打印验证结果
        # if not all_docs:
        #     print("警告：未从向量库中提取到任何 Documents！")
        # else:
        #     for i, doc in enumerate(all_docs, 1):
        #         print(f"\n--- 文档 {i} ---")
        #         print(f"元数据（metadata）：{doc.metadata}")  # 文物ID、名称等
        #         print(f"文本内容（page_content）：\n{doc.page_content[:500]}...")  # 前500字符
        # print("=" * 80 + "\n")
        # ----------------------------------------------------------------------------------
        return vector_store

    # 2. 本地无向量库，从知识图谱构建
    print("本地无 RAG 向量库，开始从知识图谱提取数据并构建...")
    # 2.1 先确保知识图谱已加载（依赖原 load_and_build_graph 函数）
    if G is None or len(node_properties) == 0:
        load_and_build_graph()
    # 2.2 从知识图谱提取 RAG 文档
    rag_docs = extract_kg_to_rag_documents()
    print(f"文档提取完成，共 {len(rag_docs)} 个文物文档（每个文物作为一个完整文本块）")

    # # 2.3 文本分块（避免单文档过长，提升检索精度）
    # text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=500,  # 每个文本块最大长度（根据模型上下文调整）
    #     chunk_overlap=50,  # 块间重叠（避免割裂上下文）
    #     separators=["\n\n", "\n", " ", ""]  # 分割符优先级
    # )
    # split_docs = text_splitter.split_documents(rag_docs)
    # print(f"文本分块完成，共 {len(split_docs)} 个文本块")

    # 2.3 取消按字符分块，保持每个文物作为一个完整文档
    # 直接使用原始文档列表，不进行分割
    final_docs = rag_docs

    # 2.4 构建向量库并保存到本地
    vector_store = FAISS.from_documents(
        documents=final_docs,
        embedding=embeddings
    )
    vector_store.save_local(VECTOR_STORE_PATH)
    print(f"RAG 向量库构建完成，已保存到：{VECTOR_STORE_PATH}")
    return vector_store


def retrieve_relevant_context(user_question, top_k=3, artifact_ids=None):
    """
    从RAG知识库中抽取与用户问题相关的内容
    参数：
        user_question: str - 用户输入的问题
        top_k: int - 检索Top N个相似文档（默认3）
        artifact_ids: list/None - 文物ID列表（如["琴1_1", "琴2_1"]）
    返回：
        str - 整合后的相关知识内容
    """
    global vector_store
    # 1. 验证向量库是否已加载
    if vector_store is None:
        vector_store = build_or_load_rag_vectorstore()
        if vector_store is None:
            print("检索失败：RAG向量库无法加载")
            return ""

    # 2. 处理artifact_ids参数（统一转换为列表格式）
    target_belongs = set()  # 强制在所有逻辑前初始化，确保作用域覆盖
    art_id_list = []

    # 明确处理artifact_ids为字符串的情况（已知输入类型为str）
    if artifact_ids is not None:
        # 由于已知是str类型，可简化判断（保留兼容逻辑）
        if isinstance(artifact_ids, str):
            # 按逗号分割并清洗字符串（如"a,b "→["a", "b"]）
            art_id_list = [x.strip() for x in artifact_ids.split(',') if x.strip()]
            print(f"[检索日志] 解析artifact_ids字符串：{artifact_ids} → 提取{len(art_id_list)}个ID")
        else:
            # 理论上不会触发（已知是str），保留容错提示
            print(f"[检索日志] artifact_ids类型异常（预期str，实际{type(artifact_ids)}）")
    else:
        # 处理artifact_ids为None的情况
        print(f"[检索日志] artifact_ids未提供（值为None）")

    # 2.2 从列表中提取所属标识（下划线后的值）
    if art_id_list:
        for art_id in art_id_list:
            parts = art_id.split("_")
            if len(parts) >= 2:  # 确保格式如"名称_归属"（如"三峡流泉_95"）
                # belongs_part = parts[-1].strip()
                belongs_part = parts[0].strip()
                if belongs_part:
                    target_belongs.add(belongs_part)
        # 无论是否提取到归属，都打印结果（确保target_belongs已定义）
        print(f"[检索日志] 从artifact_ids提取的所属标识：{target_belongs}（共{len(target_belongs)}个）")
    else:
        # 覆盖空列表情况，明确target_belongs状态
        print(f"[检索日志] 无有效artifact_ids可解析，所属标识集合保持为空：{target_belongs}")

    # 3. 优先按文档内容中的“所属标识：”筛选文档
    relevant_docs = []
    if target_belongs:
        # 获取所有文档用于筛选
        try:
            all_docs = vector_store.get_all_documents()
        except AttributeError:
            # 兼容旧版本LangChain
            all_docs = []
            for idx in range(vector_store.index.ntotal):
                doc_id = vector_store.index_to_docstore_id[idx]
                doc = vector_store.docstore.search(doc_id)
                if doc is not None:
                    all_docs.append(doc)

        # 筛选逻辑：文档内容中“所属标识：”后的数值与目标匹配
        for doc in all_docs:
            content = doc.page_content
            # 提取“所属标识：”后的内容（支持换行和空格）
            if "所属标识：" in content:
                # 分割并清洗数值（如“所属标识： 1,2 ”→提取“1,2”）
                belongs_text = content.split("所属标识：", 1)[1].split("\n", 1)[0].strip()
                if belongs_text:
                    # 文档可能包含多个所属标识（如“1,2”）
                    doc_belongs_set = set([x.strip() for x in belongs_text.split(',')])
                    # 只要有一个标识匹配就保留
                    if not target_belongs.isdisjoint(doc_belongs_set):
                        relevant_docs.append(doc)

        print(f"[检索日志] 按文档内容中所属标识筛选后得到{len(relevant_docs)}个文档")

    # 4. 若没有匹配的文档，使用相似性检索
    if not relevant_docs:
        print(f"[检索日志] 无匹配的所属标识，使用相似性检索Top {top_k}文档")
        relevant_docs = vector_store.similarity_search(
            query=user_question,
            k=top_k
        )

    # 5. 整合检索结果（去重、提取内容）
    if not relevant_docs:
        print("[检索日志] 未找到符合条件的文档")
        return "未找到相关的文物知识信息。"

    seen_artifact_ids = set()
    context_parts = []
    context_parts.append("【相关文物知识内容】")

    for idx, doc in enumerate(relevant_docs, 1):
        art_id = doc.metadata.get("artifact_id", "未知ID")
        art_name = doc.metadata.get("artifact_name", "未知文物")

        # 从文档内容中提取所属标识用于展示
        content = doc.page_content
        art_belongs = "未知归属"
        if "所属标识：" in content:
            art_belongs = content.split("所属标识：", 1)[1].split("\n", 1)[0].strip()

        if art_id in seen_artifact_ids:
            continue
        seen_artifact_ids.add(art_id)

        # 按问题关键词优化内容
        doc_content = content
        question_keywords = [kw.strip() for kw in user_question.split() if len(kw.strip()) >= 2]
        if question_keywords:
            content_sentences = doc_content.split('\n')
            relevant_sentences = [sent for sent in content_sentences if any(kw in sent for kw in question_keywords)]
            if relevant_sentences:
                doc_content = "\n".join(relevant_sentences)

        context_parts.append(
            f"{idx}. 文物：{art_name}（ID：{art_id}，归属：{art_belongs}）\n"
            f"   相关信息：\n{doc_content}\n"
            f"   {'-' * 50}\n"
        )

    final_context = "\n".join(context_parts)
    print(f"[检索日志] 提取到的相关内容：\n{final_context}")
    return final_context
# -----------------------------------------------------------------------------

# 配置文件路径
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table2.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table3.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table_updated.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table_updated2.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table_updated3.xlsx')
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'entities_table_classified_merge.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table2.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table3.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table_updated.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table_updated2.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'relations_table_updated3.xlsx')

#gqkg
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_nn3_test.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_nn3_test.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_nn3.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_nn3.xlsx')
#
#
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_with_images_new_v2.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_final_new_v2.xlsx')
#
###正确的文件
# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_eg1-3-2-images.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_eg1-3-2.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_eg1-3-2-images - 副本.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_eg1-3-2 - 副本.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'merged_entities_3.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'merged_relations_3.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'new_merged_entities_final.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'new_merged_relations_final.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'shanhai_merged_entities_layered_final.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'shanhai_merged_relations_layered_final.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'qinhan_merged_entities.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'qinhan_merged_relations.xlsx')

# ENTITIES_FILE = os.path.join(os.path.dirname(__file__), '4_merged_entities_eg1-4-l2-layered-2 - 副本.xlsx')
# RELATIONS_FILE = os.path.join(os.path.dirname(__file__), '4_merged_relations_eg1-4-l2-layered-2 - 副本.xlsx')

ENTITIES_FILE = os.path.join(os.path.dirname(__file__), 'all_books_merged_entities.xlsx')
RELATIONS_FILE = os.path.join(os.path.dirname(__file__), 'all_books_merged_relations.xlsx')
BOOKS_META_FILE = os.path.join(os.path.dirname(__file__), 'books.json')

STATIC_IMAGE_BASE = os.path.join(os.path.dirname(__file__), 'static')
STATIC_IMAGE_URL_PREFIX = 'static/'


# 初始化LLM客户端（使用代理配置）
# client = OpenAI(
#     base_url="http://38.147.105.35:3030/v1",
#     api_key="sk-ptH8ova7JyCVEzmd8pXT3CPUn5cOz2aub68b2kOlZdD20ElF",  # 替换为实际API密钥
#     http_client=httpx.Client(
#         base_url="http://38.147.105.35:3030/v1",
#         follow_redirects=True,
#     ),
# )

client = OpenAI(
    base_url="https://ssvip.dmxapi.com/v1",
    api_key="sk-5aZQx8y8RzmPX4MHT79de0pnaK8grVJtT3CpgwmPAcYiGsrI",  # 替换为实际API密钥
    http_client=httpx.Client(
        base_url="https://ssvip.dmxapi.com/v1",
        follow_redirects=True,
    ),
)

# 全局变量存储图结构和节点属性
G = None
node_properties = {}  # {节点ID: {is_artifact: 0/1, ...其他属性}}
node_relations = {}   # 修正：{属性节点ID: [{'source_node': 来源节点ID, 'relation': 关系类型}, ...]}
available_books = []  # 合并数据中存在的书目编码列表，如 ['gq', 'yjzq']
book_labels = {}  # 书目编码 -> 显示名称


def _load_book_labels():
    """从 books.json 加载书目编码与显示名映射。"""
    global book_labels
    book_labels = {}
    if not os.path.isfile(BOOKS_META_FILE):
        return
    try:
        with open(BOOKS_META_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for code, label in raw.items():
                norm_code = _normalize_book(code)
                if not norm_code:
                    continue
                text = str(label).strip() if label is not None else ''
                book_labels[norm_code] = text or norm_code
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f'[书目] 读取 {BOOKS_META_FILE} 失败: {exc}')


def _book_label(code):
    norm = _normalize_book(code)
    if not norm:
        return ''
    return book_labels.get(norm, norm)


def _format_books_payload(codes):
    """将书目编码列表转为 API 用的 {code, label} 列表。"""
    payload = []
    seen = set()
    for code in codes or []:
        norm = _normalize_book(code)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        payload.append({'code': norm, 'label': _book_label(norm)})
    return payload


def _normalize_book(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return str(value).strip().lower()


def _scoped_node_id(book, raw_entity):
    """多书合并时以 book_实体 作为图内唯一节点 ID，避免不同书同名实体冲突。"""
    raw = str(raw_entity).strip()
    book = _normalize_book(book)
    if not book:
        return raw
    prefix = f"{book}_"
    if raw.startswith(prefix):
        return raw
    return f"{book}_{raw}"


def _parse_books_query(books_param):
    """解析 ?books=eg,gq；空则返回 None 表示不过滤。"""
    if not books_param:
        return None
    books = {_normalize_book(b) for b in books_param.split(',') if b.strip()}
    return books or None


def _node_book(node_id):
    return _normalize_book(node_properties.get(node_id, {}).get('book_clean', ''))


def _parse_image_folder_paths(images_files_str):
    if not images_files_str or str(images_files_str).strip().lower() == 'nan':
        return []
    return [
        path.strip() for path in str(images_files_str).split(',')
        if path.strip() and os.path.exists(path.strip())
    ]


def _folders_to_static_urls(folder_paths):
    """将本地图片目录展开为前端可访问的 static/ URL 列表。"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    urls = []
    base_path = os.path.normpath(STATIC_IMAGE_BASE)
    for folder in folder_paths or []:
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            if not filename.lower().endswith(image_extensions):
                continue
            file_path = os.path.normpath(os.path.join(folder, filename))
            if not os.path.isfile(file_path):
                continue
            try:
                rel = os.path.relpath(file_path, base_path)
            except ValueError:
                rel = file_path.replace(base_path, '').lstrip(os.sep)
            urls.append(f"{STATIC_IMAGE_URL_PREFIX}{rel.replace(os.sep, '/')}")
    return urls


def _resolve_node_image_urls(images_files_str):
    """从总表 images_files 列解析本地目录并生成 static URL。"""
    folder_paths = _parse_image_folder_paths(images_files_str)
    return folder_paths, _folders_to_static_urls(folder_paths)


def _is_artifact_flag(value):
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return str(value).strip() in ('1', '1.0', 'true', 'True')


def _read_text_file(file_path):
    for encoding in ('utf-8', 'utf-8-sig', 'gbk'):
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError:
            return ''
    return ''


def _resolve_text_files(text_files_str):
    """
    解析 entities 表 text_files 列：逗号分隔的 .txt 路径或内联文本。
    路径存在则读文件，否则将片段当作内联描述。
    """
    if text_files_str is None or (isinstance(text_files_str, float) and pd.isna(text_files_str)):
        return ''
    raw = str(text_files_str).strip()
    if not raw or raw.lower() == 'nan':
        return ''
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    if not parts:
        return ''
    chunks = []
    for part in parts:
        if os.path.isfile(part):
            content = _read_text_file(part)
            if content.strip():
                chunks.append(content.strip())
        else:
            chunks.append(part)
    if chunks:
        return '\n\n'.join(chunks)
    return raw


def _format_node_payload(node_id):
    props = node_properties.get(node_id, {})
    return {
        'id': node_id,
        'name': props.get('original_name', node_id),
        'type': 'artifact' if props.get('is_artifact') == 1 else 'other',
        'is_artifact': props.get('is_artifact', 0),
        'pattern_mark': props.get('花纹_标记', 0),
        'location_mark': props.get('地点_标记', 0),
        'dynasty_mark': props.get('朝代_标记', 0),
        'belongs_to': props.get('belongs_to_clean', ''),
        'book': props.get('book_clean', ''),
        'book_label': _book_label(props.get('book_clean', '')),
        'related_relations': node_relations.get(node_id, []),
        'description': props.get('description', ''),
        'image_paths': props.get('image_paths', []),
        'image_urls': props.get('image_urls', []),
        'source_text': props.get('source_text', '') if _is_artifact_flag(props.get('is_artifact', 0)) else '',
    }


def _format_link_payload(u, v, data):
    return {
        'source': u,
        'target': v,
        'relation': data.get('relation', ''),
        'rel_belongs_to': data.get('rel_belongs_to', ''),
        'book': data.get('book', ''),
        'layer': data.get('layer', ''),
    }

"""
def load_and_build_graph():
    #加载数据并通过NetworkX构建图，包含节点属性
    global G, node_properties, node_relations
    # G = nx.DiGraph()
    G = nx.Graph()
    node_properties.clear()
    node_relations.clear()  # 初始化：存储属性节点的所有关联来源

    # 加载实体表，存储节点属性（包含所有列）
    entities_df = pd.read_excel(ENTITIES_FILE)
    for _, row in entities_df.iterrows():
        node_id = row['实体']
        # 提取所有属性（转为字典）
        props = row.to_dict()
        props['is_artifact'] = 1 if props['is Artifact'] != 0 else 0
        node_properties[node_id] = props
        G.add_node(node_id)

    # 加载关系表，添加边
    relations_df = pd.read_excel(RELATIONS_FILE)
    for _, row in relations_df.iterrows():
        source = row['头实体']
        target = row['尾实体']
        relation = row['关系']
        if G.has_node(source) and G.has_node(target):
            G.add_edge(source, target, relation=relation)
            # 仅为“非文物节点”记录关联关系（文物节点无需着色，无需记录）
        if node_properties.get(target, {}).get('is_artifact', 0) == 0:
            if target not in node_relations:
                node_relations[target] = []  # 用列表存储多来源关系
            # 记录：当前属性节点的关联来源（来源节点ID + 关系类型）
            node_relations[target].append({
                'source_node': source,
                'relation': relation
            })

    print(f"图构建完成：{G.number_of_nodes()}个节点，{G.number_of_edges()}条边")
    print(f"已记录 {len(node_relations)} 个属性节点的关联关系（含多来源）")
"""

"""
def load_and_build_graph():
    # 加载数据并通过NetworkX构建图，包含节点属性+关系的belongs to属性
    global G, node_properties, node_relations
    G = nx.Graph()
    node_properties.clear()
    node_relations.clear()

    # 1. 加载实体表（不变）
    entities_df = pd.read_excel(ENTITIES_FILE)
    for _, row in entities_df.iterrows():
        node_id = row['实体']
        props = row.to_dict()
        props['is_artifact'] = 1 if props['is Artifact'] != 0 else 0
        node_properties[node_id] = props
        G.add_node(node_id)

    # 2. 加载关系表（关键修改：读取关系的belongs to，存入边属性）
    relations_df = pd.read_excel(RELATIONS_FILE)
    for _, row in relations_df.iterrows():
        source = row['头实体']
        target = row['尾实体']
        relation = row['关系']
        # 读取关系表的belongs to列（转字符串避免类型问题，去空格）
        rel_belongs_to = str(row.get('belongs to', '')).strip()

        if G.has_node(source) and G.has_node(target):
            # 新增：将关系的belongs to存入边属性（key为rel_belongs_to）
            G.add_edge(source, target, relation=relation, rel_belongs_to=rel_belongs_to)

        # 原有“记录节点关联关系”的逻辑不变
        if node_properties.get(target, {}).get('is_artifact', 0) == 0:
            if target not in node_relations:
                node_relations[target] = []
            node_relations[target].append({
                'source_node': source,
                'relation': relation
            })
    print(f"图构建完成：{G.number_of_nodes()}个节点，{G.number_of_edges()}条边")
    print(f"已记录 {len(node_relations)} 个属性节点的关联关系（含多来源）")
"""

def load_and_build_graph():
    """基于已合并好的 relations 数据加载并构建图（支持多 book 合并表）"""
    global G, node_properties, node_relations, available_books
    _load_book_labels()
    G = nx.Graph()
    node_properties.clear()
    node_relations.clear()
    available_books = []

    book_stats = {}

    # 1. 加载实体表
    entities_df = pd.read_excel(ENTITIES_FILE)
    for _, row in entities_df.iterrows():
        book = _normalize_book(row.get('book', ''))
        raw_entity = str(row['实体']).strip()
        node_id = _scoped_node_id(book, raw_entity)
        display_label = raw_entity.split('_')[-1] if '_' in raw_entity else raw_entity

        belongs_to = str(row['belongs to']).strip()
        is_artifact_raw = row['is Artifact']

        node_props = row.to_dict()
        node_props['node_id'] = node_id
        node_props['is_artifact'] = is_artifact_raw
        node_props['original_name'] = display_label
        node_props['belongs_to_clean'] = belongs_to
        node_props['book_clean'] = book

        node_props['description'] = str(row.get('属性', '')) if pd.notna(row.get('属性')) else ""

        images_files_str = str(row.get('images_files', '')).strip()
        if pd.isna(row.get('images_files')):
            images_files_str = ''
        folder_paths, image_urls = _resolve_node_image_urls(images_files_str)
        node_props['image_paths'] = folder_paths
        node_props['image_urls'] = image_urls

        text_files_raw = row.get('text_files', '')
        if pd.isna(text_files_raw):
            text_files_raw = ''
        node_props['source_text'] = (
            _resolve_text_files(text_files_raw) if _is_artifact_flag(is_artifact_raw) else ''
        )

        node_properties[node_id] = node_props
        G.add_node(node_id, **node_props)

        if book:
            book_stats.setdefault(book, {'nodes': 0, 'edges': 0})
            book_stats[book]['nodes'] += 1

    # 2. 加载关系表
    relations_df = pd.read_excel(RELATIONS_FILE)
    for idx, row in relations_df.iterrows():
        book = _normalize_book(row.get('book', ''))
        original_source = _scoped_node_id(book, row['头实体'])
        original_target = _scoped_node_id(book, row['尾实体'])
        relation = row['关系']
        rel_belongs_to = str(row.get('belongs to', '')).strip()
        layer = str(row.get('层级标签', '')).strip() if pd.notna(row.get('层级标签', '')) else ''

        if original_source in G.nodes and original_target in G.nodes:
            G.add_edge(
                original_source,
                original_target,
                relation=relation,
                rel_belongs_to=rel_belongs_to,
                book=book,
                layer=layer,
            )

            if node_properties[original_target].get('is_artifact') == 0:
                if original_target not in node_relations:
                    node_relations[original_target] = []
                node_relations[original_target].append({
                    'source_node': original_source,
                    'relation': relation,
                    'rel_belongs_to': rel_belongs_to,
                })
            if book:
                book_stats.setdefault(book, {'nodes': 0, 'edges': 0})
                book_stats[book]['edges'] += 1
        else:
            print(f"警告：第{idx}条边无效，节点不存在: {original_source} -> {original_target}")

    available_books = sorted(book_stats.keys())
    print(f"\n[系统通知] 图谱构建成功！节点: {G.number_of_nodes()}, 关系: {G.number_of_edges()}")
    for book in available_books:
        stats = book_stats.get(book, {})
        print(f" - 书目 [{book}]: 节点 {stats.get('nodes', 0)}, 边 {stats.get('edges', 0)}")


# 这个函数在单击的时候被get_same_belongs_to_data替代
def get_two_hop_non_artifact(node_id):
    """查询节点两跳内is_artifact=0的节点及关联边"""
    if node_id not in G.nodes:
        return [], []

    if node_properties.get(node_id, {}).get('is_artifact', 0) != 1:
        return [], []

    # 计算两跳节点
    two_hop_nodes = set()
    first_hop = list(G.neighbors(node_id))
    two_hop_nodes.update(first_hop)
    for n in first_hop:
        two_hop_nodes.update(list(G.neighbors(n)))

    # 过滤非文物节点
    target_nodes = [
        n for n in two_hop_nodes
        if n != node_id and node_properties.get(n, {}).get('is_artifact', 0) == 0
    ]
    target_nodes.append(node_id)  # 包含自身
    target_nodes = list(set(target_nodes))

    # 筛选关联边
    target_edges = []
    for u, v, data in G.edges(data=True):
        if u in target_nodes and v in target_nodes:
            target_edges.append({
                'source': u,
                'target': v,
                'relation': data['relation']
            })
    print(target_nodes)
    print(target_edges)
    return target_nodes, target_edges


def get_same_belongs_to_data(node_id):
    """
    单击 `is_artifact = 1` 的节点时，筛选规则：
    1. 节点：belongs to 包含或等于目标节点的 belongs to
    2. 关系：belongs to 包含目标节点的 belongs to（基于已合并的关系数据）
    """
    # 1. 验证目标节点合法性（必须是存在的文物节点）
    if node_id not in G.nodes:
        return [], []  # 节点不存在，返回空
    node_props = node_properties.get(node_id, {})
    if node_props.get('is_artifact', 0) != 1:
        return [], []  # 非文物节点，返回空

    # 2. 提取目标节点的belongs to（处理多值格式，如“1,2”→转集合{'1','2'}）
    target_book = _node_book(node_id)
    target_belongs = str(node_props.get('belongs to', '')).strip()
    if not target_belongs:
        return [], []  # 目标节点无belongs to，返回空
    # 分割多值、去空格、转集合（便于后续“包含关系判断”）
    target_belongs_set = set([x.strip() for x in target_belongs.split(',')])

    # 3. 筛选节点：同 book + belongs to 包含目标
    filtered_nodes = []
    for n in G.nodes:
        if target_book and _node_book(n) != target_book:
            continue
        n_props = node_properties.get(n, {})
        n_belongs = str(n_props.get('belongs to', '')).strip()
        if not n_belongs:
            continue  # 跳过无belongs to的节点

        # 处理当前节点的belongs to为集合
        n_belongs_set = set([x.strip() for x in n_belongs.split(',')])
        # 关键规则：目标集合是当前节点集合的子集（即当前节点包含/等于目标）
        if target_belongs_set.issubset(n_belongs_set):
            filtered_nodes.append(n)

    # 4. 筛选关系：满足2个条件
    # 条件1：边的两端节点都在筛选后的节点列表中
    # 条件2：边的belongs to（已合并的多值）包含目标节点的belongs to
    filtered_edges = []
    for u, v, edge_data in G.edges(data=True):
        # 条件1：节点在筛选列表中（无向图不区分u/v顺序）
        if u not in filtered_nodes or v not in filtered_nodes:
            continue

        if target_book and _normalize_book(edge_data.get('book', '')) != target_book:
            continue

        # 条件2：边的belongs to包含目标归属（核心判断）
        edge_rel_belongs = edge_data.get('rel_belongs_to', '').strip()
        if not edge_rel_belongs:
            continue  # 跳过无归属的边
        # 边的多归属转集合（如“1,2”→{'1','2'}）
        edge_belongs_set = set([x.strip() for x in edge_rel_belongs.split(',')])
        # 判断：目标归属集合与边归属集合是否有交集（包含至少一个共同归属）
        if not target_belongs_set.isdisjoint(edge_belongs_set):
            filtered_edges.append({
                'source': u,
                'target': v,
                'relation': edge_data['relation'],
                'rel_belongs_to': edge_rel_belongs,
                'book': edge_data.get('book', ''),
                'layer': edge_data.get('layer', ''),
            })

    # 打印筛选结果（便于调试）
    print(f"筛选结果：节点{len(filtered_nodes)}个，边{len(filtered_edges)}条")
    print(f"目标归属：{target_belongs}，边筛选规则：包含目标归属中的至少一个值")
    return filtered_nodes, filtered_edges


def get_simplified_belongs_data(node_id):
    """简化筛选+全链路日志，定位问题"""
    # -------------------------- 1. 打印目标节点的核心信息 --------------------------
    print("=" * 50)
    print(f"[开始筛选] 单击的节点：{node_id}")

    # 验证节点是否存在+是文物
    if node_id not in G.nodes:
        print(f"[错误] 节点{node_id}不在图中！")
        print("=" * 50)
        return [], []
    node_props = node_properties.get(node_id, {})
    if node_props.get('is_artifact', 0) != 1:
        print(f"[错误] 节点{node_id}不是文物节点（is_artifact={node_props.get('is_artifact')}）")
        print("=" * 50)
        return [], []

    # 打印目标节点的belongs to（原始值+处理后的值）
    target_belongs_raw = node_props.get('belongs to', '无')
    target_belongs = str(target_belongs_raw).strip()
    print(f"[目标节点属性]")
    print(f"- is_artifact: {node_props.get('is_artifact')}")
    print(f"- belongs to 原始值: {target_belongs_raw}（类型：{type(target_belongs_raw)}）")
    print(f"- belongs to 处理后: {target_belongs}（类型：{type(target_belongs)}）")
    print("-" * 30)

    # -------------------------- 2. 遍历所有边，打印关键信息+筛选逻辑 --------------------------
    target_edges = []
    all_edges = list(G.edges(data=True))  # 全图所有边
    print(f"[全图边总数] {len(all_edges)}条，开始筛选...")

    for idx, (u, v, edge_data) in enumerate(all_edges):
        # 打印当前边的所有关键数据
        edge_relation = edge_data.get('relation', '无关系')
        edge_own_belongs_raw = edge_data.get('rel_belongs_to', '无')  # 边的归属原始值
        edge_own_belongs = str(edge_own_belongs_raw).strip()  # 边的归属处理后
        is_target_edge = (u == '琴底' and v == '桐木') or (u == '桐木' and v == '琴底')  # 重点盯这条边

        # 重点标记“琴底→桐木”边
        if is_target_edge:
            print(f"[重点边-{idx}] {u} ↔ {v}（关系：{edge_relation}）")
        else:
            print(f"[普通边-{idx}] {u} ↔ {v}（关系：{edge_relation}）")

        # 打印边的归属信息
        print(f"  - 边的rel_belongs_to原始值: {edge_own_belongs_raw}（类型：{type(edge_own_belongs_raw)}）")
        print(f"  - 边的rel_belongs_to处理后: {edge_own_belongs}")
        print(f"  - 目标归属: {target_belongs}")

        # 筛选逻辑+打印判断结果
        if edge_own_belongs == target_belongs:
            target_edges.append({
                'source': u,
                'target': v,
                'relation': edge_relation,
                'rel_belongs_to': edge_own_belongs
            })
            print(f"  ✅ 保留（边归属 == 目标归属）")
        else:
            print(f"  ❌ 排除（边归属 != 目标归属）")
        print("-" * 20)

    # -------------------------- 3. 打印最终结果 --------------------------
    target_nodes = set()
    for edge in target_edges:
        target_nodes.add(edge['source'])
        target_nodes.add(edge['target'])
    target_nodes = list(target_nodes)

    print(f"[筛选结果]")
    print(f"- 保留节点数：{len(target_nodes)} → {target_nodes}")
    edge_texts = [f"{e['source']}→{e['target']}" for e in target_edges]
    print(f"- 保留边数：{len(target_edges)} → {edge_texts}")
    print("=" * 50)
    return target_nodes, target_edges

def get_common_nodes(node1_id, node2_id):
    """获取两个文物节点的公共节点（非文物节点交集）"""
    # 验证两个节点都是文物
    if (node1_id not in G.nodes or node2_id not in G.nodes or
            node_properties.get(node1_id, {}).get('is_artifact', 0) != 1 or
            node_properties.get(node2_id, {}).get('is_artifact', 0) != 1):
        return [], []

    # 获取每个节点的两跳非文物节点
    nodes1, _ = get_same_belongs_to_data(node1_id)
    nodes2, _ = get_same_belongs_to_data(node2_id)

    # 计算公共节点（排除两个文物节点本身）
    set1 = set(nodes1) - {node1_id, node2_id}
    set2 = set(nodes2) - {node1_id, node2_id}
    common_nodes = list(set1 & set2)

    # 必须包含两个选中的文物节点
    result_nodes = [node1_id, node2_id] + common_nodes
    result_nodes = list(set(result_nodes))  # 去重

    # 筛选关联边（只保留节点在结果集中的边）
    target_edges = []
    for u, v, data in G.edges(data=True):
        if u in result_nodes and v in result_nodes:
            target_edges.append({
                'source': u,
                'target': v,
                'relation': data['relation']
            })
    print(target_edges)
    print(result_nodes)
    return result_nodes, target_edges

def get_multi_nodes_data(selected_node_ids):
    """
    处理多个选中的文物节点，返回：
    1. 所有选中的is_artifact=1的节点
    2. 所有belongs to包含任一选中节点belongs to值的节点
    3. 关联的边
    """
    # 1. 验证所有选中节点都是文物节点
    valid_artifact_ids = []
    for node_id in selected_node_ids:
        if node_id in G.nodes and node_properties.get(node_id, {}).get('is_artifact') == 1:
            valid_artifact_ids.append(node_id)
    if len(valid_artifact_ids) < 2:
        return [], []  # 至少需要2个有效文物节点

    target_books = {_node_book(nid) for nid in valid_artifact_ids if _node_book(nid)}

    # 2. 收集所有选中节点的belongs to值（去重合并）
    target_belongs_set = set()
    for node_id in valid_artifact_ids:
        node_props = node_properties.get(node_id, {})
        node_belongs = str(node_props.get('belongs to', '')).strip()
        if node_belongs:
            # 分割多值（如“1,2”→添加到集合）
            target_belongs_set.update([x.strip() for x in node_belongs.split(',')])

    # 3. 筛选节点：
    # - 包含所有选中的文物节点
    # - 包含belongs to包含任一目标belongs to值的节点
    filtered_nodes = set(valid_artifact_ids)  # 先加入所有选中的文物节点
    for n in G.nodes:
        if n in filtered_nodes:
            continue  # 已包含选中节点，跳过
        if target_books and _node_book(n) not in target_books:
            continue
        n_props = node_properties.get(n, {})
        n_belongs = str(n_props.get('belongs to', '')).strip()
        if not n_belongs:
            continue
        # 检查当前节点的belongs to是否包含任一目标值
        n_belongs_set = set([x.strip() for x in n_belongs.split(',')])
        if not target_belongs_set.isdisjoint(n_belongs_set):
            filtered_nodes.add(n)

    # 4. 筛选边：两端节点都在筛选结果中，且边的belongs to与目标有交集
    filtered_edges = []
    for u, v, edge_data in G.edges(data=True):
        if u not in filtered_nodes or v not in filtered_nodes:
            continue  # 节点不在筛选列表中，跳过
        edge_book = _normalize_book(edge_data.get('book', ''))
        if target_books and edge_book not in target_books:
            continue
        # 检查边的belongs to是否与目标有交集
        edge_belongs = str(edge_data.get('rel_belongs_to', '')).strip()
        if not edge_belongs:
            continue
        edge_belongs_set = set([x.strip() for x in edge_belongs.split(',')])
        if not target_belongs_set.isdisjoint(edge_belongs_set):
            filtered_edges.append({
                'source': u,
                'target': v,
                'relation': edge_data['relation'],
                'rel_belongs_to': edge_belongs,
                'book': edge_data.get('book', ''),
                'layer': edge_data.get('layer', ''),
            })

    return list(filtered_nodes), filtered_edges


# 跨书比较：按关系名 + 邻居显示名对齐（不依赖 belongs_to）
_COMPARE_CONFLICT_KEYWORDS = ('时代', '年代', '朝代', '材质', '用途', '工艺')


def _node_display_name(node_id):
    props = node_properties.get(node_id, {})
    name = str(props.get('original_name', '') or '').strip()
    return name if name else str(node_id)


def _normalize_compare_text(value):
    return str(value or '').strip()


def _artifact_one_hop_entries(artifact_id, match_mode='text'):
    """
    文物节点的一跳邻居。
    match_mode=text：比较键 relation::显示名（跨书对齐）
    match_mode=id：比较键 relation::邻居节点 ID（同库严格对齐）
    """
    entries = []
    if artifact_id not in G.nodes:
        return entries
    mode = 'id' if str(match_mode).strip().lower() == 'id' else 'text'
    for neighbor in G.neighbors(artifact_id):
        edge_data = G[artifact_id][neighbor] if G.has_edge(artifact_id, neighbor) else {}
        relation = _normalize_compare_text(edge_data.get('relation', '关联')) or '关联'
        target_name = _node_display_name(neighbor)
        tail = str(neighbor) if mode == 'id' else target_name
        compare_key = f"{relation}::{tail}"
        entries.append({
            'compare_key': compare_key,
            'relation': relation,
            'target_id': neighbor,
            'target_name': target_name,
            'is_artifact': int(node_properties.get(neighbor, {}).get('is_artifact', 0) or 0),
        })
    return entries


def _parse_compare_key(compare_key, match_mode='text'):
    """从 compare_key 解析 relation 与展示用 target_name。"""
    relation, tail = compare_key.split('::', 1)
    if str(match_mode).strip().lower() == 'id':
        return relation, tail, _node_display_name(tail)
    return relation, tail, tail


def _empty_compare_result(valid_ids, match_mode='text', reason='need_two_artifacts'):
    return {
        'meta': {
            'ready': False,
            'reason': reason,
            'cross_book': False,
            'books': [],
            'artifact_ids': valid_ids,
            'match_mode': match_mode,
            'effective_match_mode': match_mode,
            'unified': False,
        },
        'subgraph': {'nodes': [], 'links': []},
        'display_subgraph': {'layout': 'compare-align', 'nodes': [], 'links': []},
        'display_mappings': {},
        'shared_nodes': [],
        'shared_structures': [],
        'difference_structures': [],
        'missing_structures': [],
        'conflict_structures': [],
    }


def _merge_display_id(display_name):
    """跨书对齐后的虚拟合并节点 ID（按显示名）。"""
    name = _normalize_compare_text(display_name)
    return f"merge::{name}" if name else "merge::"


def _target_display_id(compare_key, target_id, target_name, shared_keys):
    if compare_key in shared_keys:
        return _merge_display_id(target_name)
    return target_id


def _resolve_display_target(e, shared_keys, display_nodes):
    """解析 display 边上的 target：共享键走 merge hub；同名 hub 已存在则复用。"""
    if e['compare_key'] in shared_keys:
        return _merge_display_id(e['target_name'])
    merge_id = _merge_display_id(e['target_name'])
    if merge_id in display_nodes:
        return merge_id
    return e['target_id']


def _build_display_subgraph(valid_ids, per_artifact, shared_keys):
    """
    将对齐后的比较视图折叠为 display_subgraph：
    - 文物节点保留物理 ID，role=artifact
    - 共享 compare_key 的邻居合并为 merge::{显示名}，role=shared
    - 其余邻居保留物理 ID，role=unique（若已有同名 hub 则复用 hub）
    """
    display_nodes = {}
    display_mappings = {}
    display_links = []
    seen_link_keys = set()

    for aid in valid_ids:
        payload = _format_node_payload(aid)
        payload['role'] = 'artifact'
        display_nodes[aid] = payload

    shared_key_meta = {}
    for aid, entries in per_artifact.items():
        for e in entries:
            key = e['compare_key']
            if key not in shared_keys:
                continue
            if key not in shared_key_meta:
                relation, target_name = key.split('::', 1)
                shared_key_meta[key] = {
                    'relation': relation,
                    'target_name': target_name,
                    'ids': [],
                    'books': set(),
                    'relations': set(),
                }
            bucket = shared_key_meta[key]
            if e['target_id'] not in bucket['ids']:
                bucket['ids'].append(e['target_id'])
            book = _node_book(e['target_id'])
            if book:
                bucket['books'].add(book)
            bucket['relations'].add(e['relation'])

    for key, meta in shared_key_meta.items():
        merge_id = _merge_display_id(meta['target_name'])
        display_mappings[merge_id] = meta['ids']
        display_nodes[merge_id] = {
            'id': merge_id,
            'name': meta['target_name'],
            'type': 'other',
            'is_artifact': 0,
            'role': 'shared',
            'compare_key': key,
            'merged_from': meta['ids'],
            'books': sorted(meta['books']),
            'relations': sorted(meta['relations']),
        }

    for aid, entries in per_artifact.items():
        for e in entries:
            if e['compare_key'] in shared_keys:
                continue
            merge_id = _merge_display_id(e['target_name'])
            if merge_id in display_nodes:
                continue
            tid = e['target_id']
            if tid not in display_nodes:
                payload = _format_node_payload(tid)
                payload['role'] = 'unique'
                display_nodes[tid] = payload

    for aid, entries in per_artifact.items():
        for e in entries:
            target = _resolve_display_target(e, shared_keys, display_nodes)
            align_mode = 'shared' if (
                e['compare_key'] in shared_keys or str(target).startswith('merge::')
            ) else 'unique'
            link_key = (str(aid), str(target), e['relation'])
            if link_key in seen_link_keys:
                continue
            seen_link_keys.add(link_key)
            display_links.append({
                'source': aid,
                'target': target,
                'relation': e['relation'],
                'book': _node_book(aid) or '',
                'layer': '',
                'rel_belongs_to': '',
                'align_mode': align_mode,
            })

    return {
        'layout': 'compare-align',
        'nodes': list(display_nodes.values()),
        'links': display_links,
    }, display_mappings


def _edge_compare_meta(source_id, target_id, relation, per_artifact):
    """从 per_artifact 解析边的 compare_key 与 target_name（用于高亮路径映射）。"""
    for aid, entries in per_artifact.items():
        if aid != source_id:
            continue
        for e in entries:
            if e['target_id'] == target_id and e['relation'] == relation:
                return e['compare_key'], e['target_name']
    target_name = _node_display_name(target_id)
    return f"{relation}::{target_name}", target_name


def _convert_highlight_path_to_display(highlight_path, per_artifact, shared_keys):
    if not highlight_path:
        return None
    node_ids = highlight_path.get('node_ids') or highlight_path.get('nodeIds') or []
    edges = highlight_path.get('edges') or []
    if not node_ids and not edges:
        return None

    display_node_ids = set()
    display_edges = []
    for edge in edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        relation = _normalize_compare_text(edge.get('relation', '关联')) or '关联'
        compare_key, target_name = _edge_compare_meta(source_id, target_id, relation, per_artifact)
        display_source = source_id
        display_target = _target_display_id(compare_key, target_id, target_name, shared_keys)
        display_node_ids.add(str(display_source))
        display_node_ids.add(str(display_target))
        display_edges.append({
            'source': display_source,
            'target': display_target,
            'relation': relation,
        })

    if not display_node_ids and node_ids:
        for nid in node_ids:
            display_node_ids.add(str(nid))

    return {
        'node_ids': list(display_node_ids),
        'edges': display_edges,
    }


def _node_description_text(node_id):
    return str(node_properties.get(node_id, {}).get('description', '') or '').strip()


def _compare_evidence_side(artifact_id, relation, target_id, target_name, present=True):
    return {
        'artifact_id': artifact_id,
        'artifact_name': _node_display_name(artifact_id),
        'book': _node_book(artifact_id) or _node_book(target_id) or '',
        'relation': relation,
        'target_id': target_id or '',
        'target_name': target_name or '',
        'description': _node_description_text(target_id) if target_id else '',
        'present': bool(present),
    }


def _attach_diff_evidence(item, per_artifact, valid_ids):
    relation = item['relation']
    sides = []
    for aid in valid_ids:
        entries = [e for e in per_artifact.get(aid, []) if e['relation'] == relation]
        if entries:
            for entry in entries:
                sides.append(_compare_evidence_side(
                    aid, entry['relation'], entry['target_id'], entry['target_name'], True
                ))
        else:
            sides.append(_compare_evidence_side(aid, relation, '', '', False))
    values = ' / '.join(item.get('values') or [])
    item['evidence'] = {
        'kind': 'compare-diff',
        'claim': f'关系「{relation}」在各文献中指向不同实体：{values}',
        'sides': sides,
    }


def _attach_missing_evidence(miss, artifact_id, per_artifact, valid_ids):
    relation = miss['relation']
    target_id = miss.get('target_id') or ''
    target_name = miss.get('target_name') or ''
    compare_key = f'{relation}::{target_name}'
    sides = [
        _compare_evidence_side(artifact_id, relation, '', target_name, False),
    ]
    for other_aid in valid_ids:
        if other_aid == artifact_id:
            continue
        found = None
        for entry in per_artifact.get(other_aid, []):
            if entry.get('compare_key') == compare_key:
                found = entry
                break
        if found:
            sides.append(_compare_evidence_side(
                other_aid, found['relation'], found['target_id'], found['target_name'], True
            ))
    if target_id:
        sides.append({
            'artifact_id': '',
            'artifact_name': '参照节点',
            'book': _node_book(target_id) or '',
            'relation': relation,
            'target_id': target_id,
            'target_name': target_name,
            'description': _node_description_text(target_id),
            'present': True,
        })
    miss['evidence'] = {
        'kind': 'compare-missing',
        'claim': f'{_node_display_name(artifact_id)} 缺少 {relation} → {target_name}',
        'sides': sides,
    }


def _attach_conflict_evidence(item, per_artifact, valid_ids):
    _attach_diff_evidence(item, per_artifact, valid_ids)
    item['evidence']['kind'] = 'compare-conflict'
    item['evidence']['claim'] = item.get('detail') or item['evidence']['claim']


def _attach_compare_evidence(difference_structures, missing_structures, conflict_structures,
                             per_artifact, valid_ids):
    for item in difference_structures:
        _attach_diff_evidence(item, per_artifact, valid_ids)
    for row in missing_structures:
        aid = row.get('artifact_id')
        for miss in row.get('missing', []):
            _attach_missing_evidence(miss, aid, per_artifact, valid_ids)
    for item in conflict_structures:
        _attach_conflict_evidence(item, per_artifact, valid_ids)


def _normalize_artifact_ids(artifact_ids):
    valid_ids = []
    for node_id in artifact_ids:
        sid = str(node_id).strip()
        if not sid:
            continue
        if sid in G.nodes and node_properties.get(sid, {}).get('is_artifact') == 1:
            valid_ids.append(sid)
    return list(dict.fromkeys(valid_ids))


def compare_artifacts_core(artifact_ids, match_mode='text'):
    """
    文物一跳结构比较核心：共享 / 差异 / 缺失 / 冲突 + 子图 + 证据。
    match_mode: text（显示名）| id（节点 ID）
    """
    mode = 'id' if str(match_mode).strip().lower() == 'id' else 'text'
    valid_ids = _normalize_artifact_ids(artifact_ids)

    if len(valid_ids) < 2:
        return _empty_compare_result(valid_ids, mode)

    books = sorted({_node_book(nid) for nid in valid_ids if _node_book(nid)})
    cross_book = len(books) > 1

    per_artifact = {aid: _artifact_one_hop_entries(aid, mode) for aid in valid_ids}
    per_artifact_keys = {
        aid: {e['compare_key'] for e in entries}
        for aid, entries in per_artifact.items()
    }

    shared_keys = set.intersection(*per_artifact_keys.values()) if per_artifact_keys else set()
    union_keys = set.union(*per_artifact_keys.values()) if per_artifact_keys else set()

    shared_structures = []
    for key in sorted(shared_keys):
        relation, _tail, target_name = _parse_compare_key(key, mode)
        shared_structures.append({
            'relation': relation,
            'target_name': target_name,
            'compare_key': key,
        })

    shared_nodes_map = {}
    for aid, entries in per_artifact.items():
        for e in entries:
            if e['compare_key'] not in shared_keys:
                continue
            if e['is_artifact'] == 1:
                continue
            name_key = _normalize_compare_text(e['target_name'])
            if name_key not in shared_nodes_map:
                shared_nodes_map[name_key] = {
                    'name': e['target_name'],
                    'ids': [],
                    'books': set(),
                    'relations': set(),
                }
            bucket = shared_nodes_map[name_key]
            if e['target_id'] not in bucket['ids']:
                bucket['ids'].append(e['target_id'])
            book = _node_book(e['target_id'])
            if book:
                bucket['books'].add(book)
            bucket['relations'].add(e['relation'])

    shared_nodes = []
    for item in shared_nodes_map.values():
        shared_nodes.append({
            'id': item['ids'][0],
            'ids': item['ids'],
            'name': item['name'],
            'books': sorted(item['books']),
            'relations': sorted(item['relations']),
        })
    shared_nodes.sort(key=lambda x: x['name'])

    relation_to_target_tails = {}
    relation_to_by_artifact = {}
    for aid, entries in per_artifact.items():
        for e in entries:
            rel = e['relation']
            tail = e['target_id'] if mode == 'id' else e['target_name']
            relation_to_target_tails.setdefault(rel, set()).add(tail)
            relation_to_by_artifact.setdefault(rel, {}).setdefault(aid, set()).add(tail)

    difference_structures = []
    for relation in sorted(relation_to_target_tails.keys()):
        target_tails = relation_to_target_tails[relation]
        if len(target_tails) <= 1:
            continue
        node_ids = set(valid_ids)
        edges = []
        if mode == 'id':
            values = sorted(_node_display_name(tid) for tid in target_tails)
        else:
            values = sorted(target_tails)
        for aid, entries in per_artifact.items():
            for e in entries:
                tail = e['target_id'] if mode == 'id' else e['target_name']
                if e['relation'] == relation and tail in target_tails:
                    node_ids.add(e['target_id'])
                    edges.append({
                        'source': aid,
                        'target': e['target_id'],
                        'relation': e['relation'],
                    })
        highlight_path = {
            'node_ids': list(node_ids),
            'edges': edges,
        }
        by_artifact = {}
        for aid, tails in relation_to_by_artifact.get(relation, {}).items():
            if mode == 'id':
                by_artifact[aid] = sorted(_node_display_name(t) for t in tails)
            else:
                by_artifact[aid] = sorted(tails)
        difference_structures.append({
            'key': f'diff-{relation}',
            'relation': relation,
            'values': values,
            'by_artifact': by_artifact,
            'highlight_path': highlight_path,
        })

    artifact_name_map = {aid: _node_display_name(aid) for aid in valid_ids}
    missing_structures = []
    for aid in valid_ids:
        has_keys = per_artifact_keys.get(aid, set())
        missing = []
        for key in sorted(union_keys - has_keys):
            relation, tail, target_name = _parse_compare_key(key, mode)
            target_id = None
            if mode == 'id':
                target_id = tail if tail in G.nodes else None
            for other_aid, entries in per_artifact.items():
                if other_aid == aid:
                    continue
                for e in entries:
                    if e['compare_key'] == key:
                        target_id = e['target_id']
                        break
                if target_id:
                    break
            if not target_id:
                continue
            if mode == 'id':
                target_name = _node_display_name(target_id)
            missing.append({
                'key': f'miss-{aid}-{relation}-{tail}',
                'relation': relation,
                'target_id': target_id,
                'target_name': target_name,
                'label': f'{relation} → {target_name}',
                'highlight_path': {
                    'node_ids': [aid, target_id],
                    'edges': [{'source': aid, 'target': target_id, 'relation': relation}],
                },
            })
        missing_structures.append({
            'artifact_id': aid,
            'artifact_name': artifact_name_map.get(aid, aid),
            'missing': missing,
            'total': len(missing),
        })

    conflict_structures = []
    for item in difference_structures:
        if not any(kw in item['relation'] for kw in _COMPARE_CONFLICT_KEYWORDS):
            continue
        conflict_structures.append({
            'key': f"conflict-{item['relation']}",
            'relation': item['relation'],
            'detail': f"候选值不一致：{' / '.join(item['values'])}",
            'highlight_path': item['highlight_path'],
        })

    subgraph_node_ids = set(valid_ids)
    for key in union_keys:
        for aid, entries in per_artifact.items():
            for e in entries:
                if e['compare_key'] == key:
                    subgraph_node_ids.add(e['target_id'])

    subgraph_links = []
    seen_edges = set()
    for u, v, data in G.edges(data=True):
        if u not in subgraph_node_ids or v not in subgraph_node_ids:
            continue
        edge_key = tuple(sorted((u, v)))
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        subgraph_links.append(_format_link_payload(u, v, data))

    subgraph_nodes = [_format_node_payload(nid) for nid in subgraph_node_ids]

    display_subgraph, display_mappings = _build_display_subgraph(
        valid_ids, per_artifact, shared_keys
    )

    for item in difference_structures:
        item['display_highlight_path'] = _convert_highlight_path_to_display(
            item.get('highlight_path'), per_artifact, shared_keys
        )
    for row in missing_structures:
        for miss in row.get('missing', []):
            miss['display_highlight_path'] = _convert_highlight_path_to_display(
                miss.get('highlight_path'), per_artifact, shared_keys
            )
    for item in conflict_structures:
        item['display_highlight_path'] = _convert_highlight_path_to_display(
            item.get('highlight_path'), per_artifact, shared_keys
        )

    _attach_compare_evidence(
        difference_structures, missing_structures, conflict_structures,
        per_artifact, valid_ids,
    )

    return {
        'meta': {
            'ready': True,
            'reason': '',
            'cross_book': cross_book,
            'books': books,
            'artifact_ids': valid_ids,
            'match_mode': mode,
            'effective_match_mode': mode,
            'unified': False,
            'display_node_count': len(display_subgraph['nodes']),
            'physical_node_count': len(subgraph_nodes),
        },
        'subgraph': {'nodes': subgraph_nodes, 'links': subgraph_links},
        'display_subgraph': display_subgraph,
        'display_mappings': display_mappings,
        'shared_nodes': shared_nodes,
        'shared_structures': shared_structures,
        'difference_structures': difference_structures,
        'missing_structures': missing_structures,
        'conflict_structures': conflict_structures,
    }


def compare_artifacts_by_text(artifact_ids):
    """跨书/跨文物比较（显示名对齐），保留兼容旧接口。"""
    return compare_artifacts_core(artifact_ids, match_mode='text')


def compare_artifacts_unified(artifact_ids, match_mode='auto'):
    """
    统一文物比较：同书 / 跨书同一套输出 schema。
    match_mode:
      - auto：默认 text；跨书时强制 text；同书可用 text（推荐）或 id
      - text：关系 + 邻居显示名
      - id：关系 + 邻居节点 ID（仅适合同库；跨书会自动回退 text）
    """
    requested = str(match_mode or 'auto').strip().lower()
    if requested not in ('auto', 'text', 'id'):
        requested = 'auto'

    valid_ids = _normalize_artifact_ids(artifact_ids)
    if len(valid_ids) < 2:
        result = _empty_compare_result(valid_ids, 'text', reason='need_two_artifacts')
        result['meta']['requested_match_mode'] = requested
        result['meta']['unified'] = True
        return result

    books = sorted({_node_book(nid) for nid in valid_ids if _node_book(nid)})
    cross_book = len(books) > 1

    effective = requested
    fallback = None
    if effective == 'auto':
        effective = 'text'
    elif effective == 'id' and cross_book:
        effective = 'text'
        fallback = 'id_not_supported_cross_book'

    result = compare_artifacts_core(valid_ids, match_mode=effective)
    result['meta']['requested_match_mode'] = requested
    result['meta']['effective_match_mode'] = effective
    result['meta']['unified'] = True
    if fallback:
        result['meta']['match_mode_fallback'] = fallback
    return result


def build_qa_context(artifact_id):
    """构建问答上下文：当前文物+两跳内非文物节点的属性和关系"""
    # 获取两跳数据
    target_nodes, target_edges = get_same_belongs_to_data(artifact_id)
    if not target_nodes:
        return f"文物「{artifact_id}」没有关联的非文物节点信息。"

    # 构建上下文字符串
    context = []
    context.append(f"当前文物：{artifact_id}（属性：{node_properties.get(artifact_id, {})}）")
    context.append("两跳内关联的非文物节点及关系：")

    # 添加节点属性
    for node in target_nodes:
        if node == artifact_id:
            continue  # 已单独列出
        props = node_properties.get(node, {})
        context.append(f"- 节点 {node}：{props}")

    # 添加关系
    for edge in target_edges:
        context.append(f"- 关系：{edge['source']} → {edge['relation']} → {edge['target']}")

    return "\n".join(context)


def build_multi_qa_context(artifact_ids):
    """构建多文物节点的问答上下文，明确标记各关系所属的文物"""
    context = []
    # 1. 收集所有选中文物的belongs to值
    all_belongs = {}
    for art_id in artifact_ids:
        props = node_properties.get(art_id, {})
        belongs = str(props.get('belongs to', '')).strip()
        all_belongs[art_id] = set([x.strip() for x in belongs.split(',')]) if belongs else set()
        context.append(f"文物 {art_id}：属性={props}，所属标识={belongs}")

    # 2. 收集所有相关节点和边
    context.append("\n关联节点及关系（按所属文物分类）：")
    for art_id, art_belongs in all_belongs.items():
        if not art_belongs:
            continue

        # 获取该文物相关的节点和边
        nodes, edges = get_same_belongs_to_data(art_id)
        if not nodes:
            context.append(f"- 文物 {art_id} 没有关联节点")
            continue

        # 标记属于当前文物的节点和关系
        context.append(f"\n【属于文物 {art_id} 的关联信息】")
        for node in nodes:
            if node == art_id:
                continue
            props = node_properties.get(node, {})
            context.append(f"- 节点 {node}：{props}")

        for edge in edges:
            # 验证边是否属于当前文物
            edge_belongs = str(edge.get('rel_belongs_to', '')).strip()
            edge_belongs_set = set([x.strip() for x in edge_belongs.split(',')]) if edge_belongs else set()
            if art_belongs & edge_belongs_set:  # 有交集则属于该文物
                context.append(
                    f"- 关系：{edge['source']} → {edge['relation']} → {edge['target']}（所属标识={edge_belongs}）")

    return "\n".join(context)


def build_all_nodes_qa_context():
    """构建包含所有文物节点的问答上下文"""
    context = []
    # 1. 收集所有文物节点
    artifact_nodes = [
        node_id for node_id, props in node_properties.items()
        if props.get('is_artifact', 0) == 1
    ]
    context.append(f"所有文物节点：{', '.join(artifact_nodes)}")

    # 2. 按文物节点分组添加关联信息
    for art_id in artifact_nodes:
        # 获取该文物的belongs to值
        art_props = node_properties.get(art_id, {})
        art_belongs = str(art_props.get('belongs to', '')).strip()
        art_belongs_set = set([x.strip() for x in art_belongs.split(',')]) if art_belongs else set()

        context.append(f"\n【文物 {art_id} 的关联信息】")
        context.append(f"- 属性：{art_props}")

        # 获取关联节点和边
        nodes, edges = get_same_belongs_to_data(art_id)
        for node in nodes:
            if node == art_id:
                continue
            props = node_properties.get(node, {})
            context.append(f"- 关联节点 {node}：{props}")

        for edge in edges:
            context.append(
                f"- 关系：{edge['source']} → {edge['relation']} → {edge['target']}（所属标识={edge.get('rel_belongs_to', '')}）")

    return "\n".join(context)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/books', methods=['GET'])
def list_books():
    """返回合并数据中可用的书目列表（含 code 与 label）。"""
    return jsonify({'books': _format_books_payload(available_books)})


@app.route('/graph-data', methods=['GET'])
def get_graph_data():
    """获取全图数据；可选 ?books=eg,gq 按书目过滤。"""
    book_filter = _parse_books_query(request.args.get('books'))

    nodes = []
    for node_id, props in node_properties.items():
        node_book = _normalize_book(props.get('book_clean', ''))
        if book_filter is not None and node_book not in book_filter:
            continue
        nodes.append(_format_node_payload(node_id))

    node_ids = {n['id'] for n in nodes}
    links = []
    for u, v, data in G.edges(data=True):
        if u not in node_ids or v not in node_ids:
            continue
        edge_book = _normalize_book(data.get('book', ''))
        if book_filter is not None and edge_book not in book_filter:
            continue
        links.append(_format_link_payload(u, v, data))

    artifact_nodes = [n for n in nodes if n['is_artifact'] == 1]
    wuming_nodes = [n for n in artifact_nodes if n['name'] == '无名琴']

    print(f"\n[接口调试] 全图数据打包完成（books={book_filter or 'all'}）：")
    print(f" - 总节点数: {len(nodes)} (文物: {len(artifact_nodes)}, 含无名琴: {len(wuming_nodes)})")
    print(f" - 总关系数: {len(links)}")

    return jsonify({
        'nodes': nodes,
        'links': links,
        'books': _format_books_payload(available_books),
    })


@app.route('/two-hop/<node_id>', methods=['GET'])
def get_two_hop(node_id):
    """获取两跳内非文物节点及边（对齐新构建逻辑与参数配置）"""
    # 1. 获取目标节点和边数据
    # 确保 get_same_belongs_to_data 返回的是包含 data 的边 (u, v, data)
    target_nodes, target_edges = get_same_belongs_to_data(node_id)

    # 2. 格式化节点数据
    nodes_with_type = []
    for n in target_nodes:
        if n not in node_properties:
            continue
        nodes_with_type.append(_format_node_payload(n))

    # 3. 核心修复：格式化边数据，补全 relation 和 rel_belongs_to
    formatted_links = []
    for edge in target_edges:
        # 如果 edge 是元组 (u, v, data)
        if isinstance(edge, tuple) and len(edge) == 3:
            u, v, data = edge
            formatted_links.append(_format_link_payload(u, v, data))
        # 如果 edge 已经是字典且包含 data
        elif isinstance(edge, dict):
            formatted_links.append(edge)

    return jsonify({
        'nodes': nodes_with_type,
        'links': formatted_links
    })


@app.route('/common-nodes/<node1_id>/<node2_id>', methods=['GET'])
def get_common_nodes_api(node1_id, node2_id):
    """获取两个文物节点的公共节点及关联边（对齐新构建逻辑与参数配置）"""
    # 1. 获取公共节点和边数据
    # 注意：确保 get_common_nodes 返回的是 (u, v, data) 格式的边列表
    target_nodes, target_edges = get_common_nodes(node1_id, node2_id)

    # 2. 格式化节点数据
    nodes_with_type = []
    for n in target_nodes:
        if n not in node_properties:
            continue

        props = node_properties[n]
        nodes_with_type.append({
            'id': n,
            'name': props.get('original_name', n),  # 显示拆分后的纯净名称
            'type': 'artifact' if props.get('is_artifact') == 1 else 'other',

            # 传递标记字段
            'is_artifact': props.get('is_artifact', 0),
            'pattern_mark': props.get('花纹_标记', 0),
            'location_mark': props.get('地点_标记', 0),
            'dynasty_mark': props.get('朝代_标记', 0),

            # 传递关联关系与归属
            'related_relations': node_relations.get(n, []),
            'belongs_to': props.get('belongs_to_clean', ''),  # 保持与原参数名一致

            # 补充内容属性（用于详情显示）
            'description': props.get('description', ''),
            'image_paths': props.get('image_paths', [])
        })

    # 3. 核心修复：格式化边数据，补全 relation 和 rel_belongs_to
    formatted_links = []
    for edge in target_edges:
        # 如果 edge 是 NetworkX 标准的 (u, v, data) 元组
        if isinstance(edge, tuple) and len(edge) == 3:
            u, v, data = edge
            formatted_links.append({
                'source': u,
                'target': v,
                'relation': data.get('relation', ''),
                'rel_belongs_to': data.get('rel_belongs_to', '')  # 确保关系归属正确传递
            })
        # 兼容性处理：如果是字典格式
        elif isinstance(edge, dict):
            formatted_links.append(edge)

    return jsonify({
        'nodes': nodes_with_type,
        'links': formatted_links
    })


@app.route('/qa/<artifact_id>', methods=['POST'])
def qa_interface(artifact_id):
    """智能问答接口：用英文约束LLM，要求返回中文答案"""
    try:
        # 获取用户问题
        data = request.get_json()
        question = data.get('question', '')
        if not question:
            return jsonify({'error': '问题不能为空'}), 400

        # 构建上下文（文物+两跳内非文物节点信息）
        # context = build_qa_context(artifact_id)

        art_props = node_properties.get(artifact_id, {})
        art_belongs = art_props.get('belongs_to_clean', None)
        print(artifact_id)
        relevant_context = retrieve_relevant_context(
            user_question=question,
            top_k=3,
            artifact_ids=artifact_id  # 仅检索与该文物归属一致的内容
        )

        # 构建LLM提示词（用英文约束，要求中文回答）
        prompt = f"""Answer the user's question based solely on the provided information about the cultural relic and its related nodes.

Constraints:
1. You must only use the information provided below. Do not fabricate any content.
3. Your answer must be concise, accurate, and directly reflect the content in the provided information.
4. Regardless of the input language, your answer must be in Chinese.

Possible operations:
1. Based on the provided information, explore potential correlations among them.
2. Based on the given question, analyze whether it is related to the given information, and if it is, use relevant content to answer.

Provided information:
{relevant_context}

User's question: {question}
"""
        # ======================打印传给LLM的文本======================
        print("\n" + "=" * 50)
        print(f"[单节点问答] 传给LLM的文本（artifact_id: {artifact_id}）:")
        print("-" * 50)
        print(prompt)
        print("=" * 50 + "\n")
        # ======================打印传给LLM的文本结束======================

        # 调用LLM
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an assistant that answers questions based strictly on provided information. Follow all constraints carefully."},
                {"role": "user", "content": prompt}
            ]
        )

        # 提取回答
        answer = completion.choices[0].message.content.strip()
        return jsonify({'answer': answer})

    except Exception as e:
        print(f"问答接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500

@app.route('/multi-qa/<artifact_ids>', methods=['POST'])
def multi_qa_interface(artifact_ids):
    """多文物节点问答接口"""
    try:
        # 解析选中的文物ID
        art_ids = artifact_ids.split(',')
        # 验证所有节点都是文物
        valid_arts = [id for id in art_ids if id in G.nodes and node_properties.get(id, {}).get('is_artifact') == 1]
        if not valid_arts:
            return jsonify({'error': '请选择有效的文物节点'}), 400

        # 获取用户问题
        data = request.get_json()
        question = data.get('question', '')
        if not question:
            return jsonify({'error': '问题不能为空'}), 400

        # 构建多文物上下文
        # context = build_multi_qa_context(valid_arts)

        # 3. 新增：从RAG知识库提取相关内容（按多个文物的belongs_to联合筛选）
        # 收集所有选中文物的belongs_to（去重，用逗号拼接）
        all_belongs = set()

        print(type(artifact_ids))

        for art_id in valid_arts:
            art_props = node_properties.get(art_id, {})
            art_belongs = art_props.get('belongs_to_clean', '')
            if art_belongs:
                all_belongs.update([x.strip() for x in art_belongs.split(',')])
        filter_belongs = ','.join(all_belongs) if all_belongs else None

        relevant_context = retrieve_relevant_context(
            user_question=question,
            top_k=5,  # 多文物场景可适当增加top_k（如5）
            artifact_ids=artifact_ids  # 筛选所有选中文物归属的内容
        )

        # 构建LLM提示词
        prompt = f"""Answer the user's question based solely on the provided information about multiple cultural relics and their related nodes.

Constraints:
1. You must only use the information provided below. Do not fabricate any content.
2. Clearly distinguish relationships belonging to different cultural relics according to their "belongs to" identifiers.
4. Your answer must be concise, accurate, and directly reflect the content in the provided information.
5. Regardless of the input language, your answer must be in Chinese.

Possible operations:
1. Based on the provided information, explore potential correlations among them.
2. Based on the given question, analyze whether it is related to the given information, and if it is, use relevant content to answer.

Provided information:
{relevant_context}

User's question: {question}
"""
        # ======================打印传给LLM的文本======================
        print("\n" + "=" * 50)
        print(f"[多节点问答] 传给LLM的文本（artifact_ids: {artifact_ids}）:")
        print("-" * 50)
        print(prompt)
        print("=" * 50 + "\n")
        # ======================打印传给LLM的文本结束======================


        # 调用LLM
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an assistant that answers questions based strictly on provided information. Follow all constraints carefully."},
                {"role": "user", "content": prompt}
            ]
        )

        # 提取回答
        answer = completion.choices[0].message.content.strip()
        return jsonify({'answer': answer})

    except Exception as e:
        print(f"多节点问答接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500

@app.route('/all-nodes-qa', methods=['POST'])
def all_nodes_qa_interface():
    """全节点问答接口：未选中任何节点时使用"""
    try:
        # 获取用户问题
        data = request.get_json()
        question = data.get('question', '')
        if not question:
            return jsonify({'error': '问题不能为空'}), 400

        # 构建全节点上下文
        # context = build_all_nodes_qa_context()

        # 2. 新增：从RAG知识库提取相关内容（不筛选belongs_to，检索全库）
        relevant_context = retrieve_relevant_context(
            user_question=question,
            top_k=5  # 全库场景适当增加top_k，确保覆盖所有可能相关的文物
        )

        # 构建LLM提示词
        prompt = f"""Answer the user's question based solely on the provided information about all cultural relics and their related nodes.

Constraints:
1. You must only use the information provided below. Do not fabricate any content.
2. Clearly distinguish relationships belonging to different cultural relics according to their "belongs to" identifiers.

4. Your answer must be concise, accurate, and directly reflect the content in the provided information.
5. Regardless of the input language, your answer must be in Chinese.

Possible operations:
1. Based on the provided information, explore potential correlations among them.
2. Based on the given question, analyze whether it is related to the given information, and if it is, use relevant content to answer.

Provided information:
{relevant_context}

User's question: {question}
"""
        # ======================打印传给LLM的文本======================
        print("\n" + "=" * 50)
        print(f"[全节点问答] 传给LLM的文本:")
        print("-" * 50)
        print(prompt)
        print("=" * 50 + "\n")
        # ======================打印传给LLM的文本结束======================
        # 调用LLM
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an assistant that answers questions based strictly on provided information. Follow all constraints carefully."},
                {"role": "user", "content": prompt}
            ]
        )

        # 提取回答
        answer = completion.choices[0].message.content.strip()
        return jsonify({'answer': answer})

    except Exception as e:
        print(f"全节点问答接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500


@app.route('/multi-nodes/<nodes_param>', methods=['GET'])
def multi_nodes(nodes_param):
    """处理多个选中节点的请求"""
    # 解析前端传递的节点ID（逗号分隔）
    selected_node_ids = nodes_param.split(',')
    nodes, edges = get_multi_nodes_data(selected_node_ids)

    # 构造返回数据（补充节点属性）
    result_nodes = []
    for node_id in nodes:
        props = node_properties.get(node_id, {})
        result_nodes.append({
            'id': node_id,
            'name': props.get('original_name', node_id),  # 原始名称显示
            'is_artifact': props.get('is_artifact', 0),
            'related_relations': node_relations.get(node_id, []),  # 用于前端着色
            # 'belongs_to': props.get('belongs to', '').strip()  # 关键修改
            # 'belongs_to': str(props.get('belongs to', '')).strip()  # 先转为字符串再去空格
            'belongs_to': props.get('belongs_to_clean', '')
        })
    return jsonify({'nodes': result_nodes, 'links': edges})


@app.route('/compare-artifacts', methods=['POST'])
def compare_artifacts():
    """
    跨书文物比较：按关系类型 + 邻居显示名对齐，不依赖 belongs_to。
    请求体：{"artifact_ids": ["gq_8_襄", "yjzq_8_襄"]}
    """
    try:
        data = request.get_json(silent=True) or {}
        raw_ids = data.get('artifact_ids') or data.get('ids') or []
        if isinstance(raw_ids, str):
            raw_ids = [x.strip() for x in raw_ids.split(',') if x.strip()]
        if not isinstance(raw_ids, list):
            return jsonify({'error': 'artifact_ids 必须为数组'}), 400
        result = compare_artifacts_by_text(raw_ids)
        if not result['meta']['ready']:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        print(f"跨书比较接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500


@app.route('/artifact-compare', methods=['POST'])
def artifact_compare_unified():
    """
    统一文物比较（同书 / 跨书）：共享、差异、缺失、冲突、证据链、display_subgraph。
    请求体：
      {
        "artifact_ids": ["gq_8_襄", "yjzq_8_襄"],
        "match_mode": "auto"   // auto | text | id，默认 auto（等价 text；跨书 id 会回退 text）
      }
    保留 /compare-artifacts 与 /multi-nodes 不变，本接口为工作台推荐入口。
    """
    try:
        data = request.get_json(silent=True) or {}
        raw_ids = data.get('artifact_ids') or data.get('ids') or []
        if isinstance(raw_ids, str):
            raw_ids = [x.strip() for x in raw_ids.split(',') if x.strip()]
        if not isinstance(raw_ids, list):
            return jsonify({'error': 'artifact_ids 必须为数组'}), 400
        match_mode = data.get('match_mode') or data.get('matchMode') or 'auto'
        result = compare_artifacts_unified(raw_ids, match_mode=match_mode)
        if not result['meta']['ready']:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        print(f"统一比较接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500


@app.route('/part-taxonomy', methods=['GET'])
def part_taxonomy():
    """部件对照用标准部件表与语义层配置。"""
    try:
        return jsonify(get_part_taxonomy())
    except Exception as e:
        print(f"部件 taxonomy 接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500


@app.route('/part-compare', methods=['POST'])
def part_compare():
    """
    部件级跨琴/跨书对照：按 (标准部件, 谓词) slot 对齐。
    请求体：
      {
        "artifact_ids": ["gq_14_襄", "yjzq_8_襄"],
        "parts": ["龙池", "琴体"],
        "diff_kinds": ["V", "A"]
      }
    """
    try:
        data = request.get_json(silent=True) or {}
        raw_ids = data.get('artifact_ids') or data.get('ids') or []
        if isinstance(raw_ids, str):
            raw_ids = [x.strip() for x in raw_ids.split(',') if x.strip()]
        if not isinstance(raw_ids, list):
            return jsonify({'error': 'artifact_ids 必须为数组'}), 400
        parts_filter = data.get('parts') or data.get('parts_filter') or []
        diff_kind_filter = data.get('diff_kinds') or data.get('diff_kind_filter') or []
        result = compare_parts_core(
            raw_ids,
            G,
            node_properties,
            book_label_fn=_book_label,
            parts_filter=parts_filter if parts_filter else None,
            diff_kind_filter=diff_kind_filter if diff_kind_filter else None,
        )
        if not result['meta']['ready']:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        print(f"部件对照接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500


"""根据非文物节点的belongs to值查询相关文物节点及直接关联边"""


@app.route('/non-artifact-related/<node_id>', methods=['GET'])
def get_non_artifact_related(node_id):
    """
    根据非文物节点查询相关文物节点：
    1. 提取非文物节点的belongs to值集合
    2. 筛选belongs to包含该集合任一值的文物节点
    3. 只保留非文物节点与这些文物节点的直接关联边
    """
    # 1. 验证节点是否为非文物节点
    if node_id not in G.nodes:
        return jsonify({"nodes": [], "links": []})

    node_props = node_properties.get(node_id, {})
    if node_props.get('is_artifact', 1) == 1:  # 确保是non-artifact节点
        return jsonify({"nodes": [], "links": []})

    # 2. 提取非文物节点的belongs to值集合
    node_belongs = str(node_props.get('belongs_to_clean', '')).strip()
    if not node_belongs:
        return jsonify({"nodes": [], "links": []})

    node_belongs_set = set([x.strip() for x in node_belongs.split(',')])

    # 3. 筛选相关文物节点（belongs to有交集）
    related_artifact_nodes = []
    for n in G.nodes:
        n_props = node_properties.get(n, {})
        # 只处理文物节点
        if n_props.get('is_artifact', 0) != 1:
            continue

        # 检查文物节点的belongs to是否有交集
        art_belongs = str(n_props.get('belongs_to_clean', '')).strip()
        if not art_belongs:
            continue

        art_belongs_set = set([x.strip() for x in art_belongs.split(',')])
        if not node_belongs_set.isdisjoint(art_belongs_set):
            related_artifact_nodes.append(n)

    # 4. 筛选直接关联边（非文物节点与相关文物节点之间的边）
    related_edges = []
    for u, v, edge_data in G.edges(node_id, data=True):
        # 检查另一端是否为相关文物节点
        other_node = v if u == node_id else u
        if other_node in related_artifact_nodes:
            related_edges.append({
                "source": u,
                "target": v,
                "relation": edge_data.get('relation', '')
            })

    # 5. 构建结果节点列表（包含当前非文物节点+相关文物节点）
    result_nodes = [node_id] + related_artifact_nodes
    result_nodes = [
        {
            "id": n,
            "name": node_properties[n].get('original_name', n),
            "is_artifact": node_properties[n].get('is_artifact', 0),
            "belongs_to": node_properties[n].get('belongs_to_clean', ''),
            "related_relations": node_relations.get(n, []),
            "description": node_properties[n].get('description', '')
        }
        for n in list(set(result_nodes))
    ]

    return jsonify({
        "nodes": result_nodes,
        "links": related_edges
    })

@app.route('/get-artifact-images/<path:artifact_id>', methods=['GET'])
def get_artifact_images(artifact_id):
    """
    根据文物节点ID，返回该文物的所有有效图片路径
    :param artifact_id: 文物节点唯一ID（如 yjzq_14_襄）
    """
    try:
        if artifact_id not in node_properties:
            return jsonify({"error": f"文物节点{artifact_id}不存在"}), 404
        if not _is_artifact_flag(node_properties[artifact_id].get('is_artifact', 0)):
            return jsonify({"error": f"节点{artifact_id}不是文物节点"}), 400

        props = node_properties[artifact_id]
        all_image_paths = list(props.get('image_urls') or [])
        if not all_image_paths:
            all_image_paths = _folders_to_static_urls(props.get('image_paths', []))

        if not all_image_paths:
            return jsonify({"image_paths": [], "msg": "该文物无关联图片"}), 200

        return jsonify({
            "image_paths": all_image_paths,
            "artifact_name": props.get('original_name', artifact_id),
            "count": len(all_image_paths),
        }), 200

    except Exception as e:
        return jsonify({"error": f"服务器错误：{str(e)}"}), 500


@app.route('/get-artifact-text/<path:artifact_id>', methods=['GET'])
def get_artifact_text(artifact_id):
    """根据文物节点 ID 返回原文（来自 text_files 列解析结果）。"""
    try:
        if artifact_id not in node_properties:
            return jsonify({"error": f"文物节点{artifact_id}不存在"}), 404
        if not _is_artifact_flag(node_properties[artifact_id].get('is_artifact', 0)):
            return jsonify({"error": f"节点{artifact_id}不是文物节点"}), 400

        props = node_properties[artifact_id]
        source_text = str(props.get('source_text', '') or '').strip()

        if not source_text:
            return jsonify({
                "source_text": "",
                "artifact_name": props.get('original_name', artifact_id),
                "msg": "该文物无关联原文",
            }), 200

        return jsonify({
            "source_text": source_text,
            "artifact_name": props.get('original_name', artifact_id),
            "length": len(source_text),
        }), 200

    except Exception as e:
        return jsonify({"error": f"服务器错误：{str(e)}"}), 500


# @app.route('/story-line/chat/<artifact_id>', methods=['POST'])  # 改接口名更贴合交互
# def story_line_chat(artifact_id):
#     """文物故事线对话接口：支持生成/讨论，复用QA的RAG逻辑"""
#     try:
#         # 1. 获取用户真实问题（而非仅“生成要求”）
#         data = request.get_json()
#         user_question = data.get('question', '').strip()  # 改字段名为question，贴合问答
#         if not user_question:
#             return jsonify({'error': '问题不能为空'}), 400
#
#         # 2. 复用QA的RAG逻辑，检索用户真实问题的上下文（而非硬编码生成指令）
#         artifact_name = node_properties.get(artifact_id, {}).get('original_name', artifact_id)
#         relevant_context = retrieve_relevant_context(
#             user_question=user_question,  # 用用户真实问题检索，而非硬编码
#             top_k=3,
#             artifact_ids=artifact_id
#         )
#
#         # 3. 重构Prompt：支持生成+讨论，贴合多轮交互
#         prompt = f"""You are a professional cultural relic storyline expert.
# You need to respond to the user's questions about {artifact_name} storyline based on the provided information.
# Rules:
# 1. Only use the provided information, do not fabricate core content.
# 2. If the user asks to generate a storyline (e.g., "生成简单故事" / "详细讨论细节"), generate a vivid, easy-to-understand storyline.
# 3. If the user asks discussion questions (e.g., "这个文物的背景是什么" / "故事线可以修改开头吗"), answer in a conversational way.
# 4. All responses must be in Simplified Chinese.
#
# Provided information:
# {relevant_context}
#
# User's question: {user_question}
# Cultural relic name: {artifact_name}
# """
#         # 打印调试
#         print("\n" + "=" * 50)
#         print(f"[故事线对话] 传给LLM的文本（artifact_id: {artifact_id}）:")
#         print("-" * 50)
#         print(prompt)
#         print("=" * 50 + "\n")
#
#         # 4. 调用LLM（system角色改为对话专家，支持多轮）
#         completion = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system",
#                  "content": "You are a professional cultural relic storyline expert, good at generating storylines and discussing related issues with users in a conversational way."},
#                 {"role": "user", "content": prompt}
#             ]
#         )
#
#         # 5. 返回通用的answer字段（而非仅storyline），贴合问答
#         answer = completion.choices[0].message.content.strip()
#         return jsonify({'answer': answer})
#
#     except Exception as e:
#         print(f"故事线对话接口错误：{str(e)}")
#         return jsonify({'error': f"处理失败：{str(e)}"}), 500

@app.route('/story-line/chat/<artifact_id>', methods=['POST'])
def story_line_chat(artifact_id):
    """文物故事线对话接口：支持按类型生成（工艺/传承演变）"""
    try:
        # 1. 获取请求参数（新增 story_line_type）
        data = request.get_json()
        user_question = data.get('question', '').strip()
        story_line_type = data.get('story_line_type', '').strip()  # 新增：接收故事线类型
        if not user_question:
            return jsonify({'error': '问题不能为空'}), 400

        # 2. 基础上下文检索（原有逻辑）
        artifact_name = node_properties.get(artifact_id, {}).get('original_name', artifact_id)
        relevant_context = retrieve_relevant_context(
            user_question=user_question,
            top_k=3,
            artifact_ids=artifact_id
        )

        # 3. 新增：根据故事线类型定制Prompt模板
        # 定义不同类型的Prompt规则
        story_type_prompt = {
            # 文物工艺：侧重制作工艺、材料、技法、工序
            'craft': """
特别规则：
- 重点围绕{artifact_name}的制作工艺展开，包括但不限于：材料选择、制作工序、核心技法、工艺特点、技术难度等。
- 故事线需具象化工艺细节，比如“如何选材”“如何雕刻”“工艺的独特性”等。
""",
            # 传承演变：侧重历史传承、时代演变、地域传播、文化影响
            'inheritance': """
特别规则：
- 重点围绕{artifact_name}的传承与演变展开，包括但不限于：历史背景、传承脉络、时代变化、地域传播、文化影响等。
- 故事线需体现时间维度的演变，比如“起源-发展-传承-现状”的逻辑。
""",
            # 默认：保持原有通用规则
            '': ""
        }

        # 拼接最终Prompt
        prompt = f"""You are a professional cultural relic storyline expert. 
You need to respond to the user's questions about {artifact_name} storyline based on the provided information.
Rules:
1. Only use the provided information, do not fabricate core content.
2. If the user asks to generate a storyline (e.g., "生成简单故事" / "详细讨论细节"), generate a vivid, easy-to-understand storyline.
3. If the user asks discussion questions (e.g., "这个文物的背景是什么" / "故事线可以修改开头吗"), answer in a conversational way.
4. All responses must be in Simplified Chinese.
{story_type_prompt[story_line_type]}  

Provided information:
{relevant_context}

User's question: {user_question}
Cultural relic name: {artifact_name}
"""

        # 调试日志（新增故事线类型）
        print("\n" + "=" * 50)
        print(f"[故事线对话] artifact_id: {artifact_id} | 故事线类型: {story_line_type}")
        print("-" * 50)
        print(prompt)
        print("=" * 50 + "\n")

        # 4. 调用LLM（保持原有逻辑，Prompt已定制）
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are a professional cultural relic storyline expert, good at generating storylines and discussing related issues with users in a conversational way."},
                {"role": "user", "content": prompt}
            ]
        )

        # 5. 返回结果
        answer = completion.choices[0].message.content.strip()
        return jsonify({'answer': answer, 'story_line_type': story_line_type})

    except Exception as e:
        print(f"故事线对话接口错误：{str(e)}")
        return jsonify({'error': f"处理失败：{str(e)}"}), 500

def main():
    load_and_build_graph()
    build_or_load_rag_vectorstore(force_rebuild=False)
    # build_or_load_rag_vectorstore(force_rebuild=True)
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(host='0.0.0.0', port=5001, debug=True)


if __name__ == '__main__':
    main()
