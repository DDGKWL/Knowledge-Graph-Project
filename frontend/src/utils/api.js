import axios from "axios";

const request = axios.create({ baseURL: "/", timeout: 10000 });

export const getBooks = () => request.get("/books");

/** @param {string[]|string|undefined} books 书目编码，如 ['gq'] 或 'gq,yjzq'；不传则返回全部 */
export const getGraphData = (books) => {
  const params = {};
  if (books != null && books !== "") {
    const list = Array.isArray(books)
      ? books.map((b) => (b && typeof b === "object" ? b.code : b)).filter(Boolean)
      : [books];
    const bookStr = list.map((b) => String(b).trim()).filter(Boolean).join(",");
    if (bookStr) params.books = bookStr;
  }
  return request.get("/graph-data", { params });
};
export const getTwoHop = (id) => request.get(`/two-hop/${encodeURIComponent(id)}`);
export const getMultiNodes = (ids) => request.get(`/multi-nodes/${encodeURIComponent(ids)}`);
/** 跨书文物比较：按关系 + 邻居显示名对齐（POST body: { artifact_ids: string[] }） */
export const postCompareArtifacts = (artifactIds) =>
  request.post("/compare-artifacts", { artifact_ids: artifactIds });

/**
 * 统一文物比较（同书/跨书，工作台推荐）
 * @param {string[]} artifactIds
 * @param {{ matchMode?: 'auto'|'text'|'id' }} options
 */
export const postArtifactCompare = (artifactIds, options = {}) => {
  const match_mode = options.matchMode || options.match_mode || "auto";
  return request.post("/artifact-compare", {
    artifact_ids: artifactIds,
    match_mode,
  });
};
export const getNonArtifactRelated = (id) =>
  request.get(`/non-artifact-related/${encodeURIComponent(id)}`);

export const getArtifactImages = (artifactId) =>
  request.get(`/get-artifact-images/${encodeURIComponent(artifactId)}`)

export const getArtifactText = (artifactId) =>
  request.get(`/get-artifact-text/${encodeURIComponent(artifactId)}`)

/** 部件对照标准表 */
export const getPartTaxonomy = () => request.get("/part-taxonomy");

/**
 * 部件级跨琴/跨书对照
 * @param {string[]} artifactIds
 * @param {{ parts?: string[], diffKinds?: string[] }} options
 */
export const postPartCompare = (artifactIds, options = {}) => {
  const body = { artifact_ids: artifactIds };
  const parts = options.parts || options.partsFilter;
  const diffKinds = options.diffKinds || options.diff_kind_filter;
  if (parts?.length) body.parts = parts;
  if (diffKinds?.length) body.diff_kinds = diffKinds;
  return request.post("/part-compare", body);
};

export const postStoryChat = (artifactId, question) => {
  return request.post(`/story-line/chat/${encodeURIComponent(artifactId)}`,
    { question },
    { timeout: 60000 }
  );
};

// export const postQA = (nodes, question) => {
//   const url = nodes.length === 1 ? `/qa/${nodes[0]}` : "/all-nodes-qa";
//   return request.post(url, { question });
// };

export const postQA = (nodes, question) => {
  const ids = (nodes || []).map((id) => String(id).trim()).filter(Boolean);
  const q = String(question || "").trim();
  if (!ids.length) {
    return Promise.reject(new Error("请先选择文物节点"));
  }
  if (!q) {
    return Promise.reject(new Error("问题不能为空"));
  }
  const url =
    ids.length === 1
      ? `/qa/${encodeURIComponent(ids[0])}`
      : `/multi-qa/${encodeURIComponent(ids.join(","))}`;
  return request.post(url, { question: q }, { timeout: 90000 });
};