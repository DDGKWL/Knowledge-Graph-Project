import * as d3 from "d3";
import { DEFAULT_COLORS, BOOK_COLOR_MAP, RELATION_COLOR_MAP } from "./graphConfig";
import {
  applyGraphLayout,
  clearFixedPositions,
  computeDegreeMap,
} from "./graphLayout";
import { getTwoHop, getMultiNodes, getNonArtifactRelated } from "./api";

function resolveNodeFill(d) {
  if (d.role === "shared") return DEFAULT_COLORS.shared;
  if (d.role === "unique") return DEFAULT_COLORS.unique;
  if (d.is_artifact === 1) {
    const book = String(d.book || "").trim().toLowerCase();
    if (book && BOOK_COLOR_MAP[book]) return BOOK_COLOR_MAP[book];
    return DEFAULT_COLORS.artifact;
  }
  return DEFAULT_COLORS.other;
}

/** 跨书比较对齐布局：左/右文物 + 中间共享 hub + 两侧独有邻居 */
function applyCompareAlignLayout(nodes, links, width, height) {
  const artifacts = nodes.filter((n) => n.role === "artifact");
  if (artifacts.length !== 2) return false;

  const shared = nodes.filter((n) => n.role === "shared");
  const artifactIds = artifacts.map((a) => String(a.id));
  const uniqueByArtifact = Object.fromEntries(artifactIds.map((id) => [id, []]));

  links.forEach((l) => {
    const src = String(l.source?.id ?? l.source);
    const tgt = String(l.target?.id ?? l.target);
    if (!artifactIds.includes(src)) return;
    const node = nodes.find((n) => String(n.id) === tgt);
    if (node?.role === "unique") uniqueByArtifact[src].push(node);
  });

  const padY = 56;
  const centerX = width / 2;
  const leftX = Math.max(90, width * 0.14);
  const rightX = Math.min(width - 90, width * 0.86);

  artifacts[0].fx = leftX;
  artifacts[0].fy = height / 2;
  artifacts[1].fx = rightX;
  artifacts[1].fy = height / 2;

  const sharedGap = Math.min(52, (height - padY * 2) / Math.max(shared.length, 1));
  const sharedBlock = shared.length * sharedGap;
  let sharedStart = (height - sharedBlock) / 2 + sharedGap / 2;
  shared.forEach((n, i) => {
    n.fx = centerX;
    n.fy = sharedStart + i * sharedGap;
  });

  function layoutUniqueSide(artifactId, baseX, sign) {
    const list = uniqueByArtifact[artifactId] || [];
    const gap = Math.min(34, (height - padY * 2) / Math.max(list.length, 1));
    const block = list.length * gap;
    let start = (height - block) / 2 + gap / 2;
    list.forEach((n, i) => {
      n.fx = baseX + sign * 120;
      n.fy = start + i * gap;
    });
  }
  layoutUniqueSide(artifactIds[0], leftX, -1);
  layoutUniqueSide(artifactIds[1], rightX, 1);
  return true;
}

function isCompareAlignLayout(data) {
  return data?.layout === "compare-align" && data.nodes?.some((n) => n.role);
}

function getThumbUrl(d) {
  const urls = d?.image_urls || d?.imageUrls || [];
  return urls.length ? String(urls[0]) : "";
}

function getNodeModality(d) {
  const hasImg = Boolean(getThumbUrl(d));
  const hasText = Boolean(
    String(d?.description || d?.source_text || d?.sourceText || "").trim()
  );
  if (hasImg && hasText) return "both";
  if (hasImg) return "img";
  if (hasText) return "txt";
  return "";
}

function modalityBadgeText(d) {
  const m = getNodeModality(d);
  if (m === "both") return "图文";
  if (m === "img") return "图";
  if (m === "txt") return "文";
  return "";
}

function nodeTooltip(d) {
  const parts = [d.name || d.id];
  if (d.book_label) parts.push(`书目：${d.book_label}`);
  if (d.description) parts.push(String(d.description).slice(0, 200));
  return parts.join("\n");
}

function linkPathD(d, curved) {
  const sx = d.source.x;
  const sy = d.source.y;
  const tx = d.target.x;
  const ty = d.target.y;
  if (!curved) return `M${sx},${sy}L${tx},${ty}`;
  const dx = tx - sx;
  const dy = ty - sy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const dr = dist * 1.35;
  return `M${sx},${sy}A${dr},${dr} 0 0,1 ${tx},${ty}`;
}

function relationMatchesFilter(d, filter) {
  if (!filter) return true;
  const rel = d.relation || d.label || "";
  return rel === filter;
}

let localFullData = null;

const DEFAULT_VIZ_OPTIONS = {
  layoutMode: "force",
  showLinkLabels: true,
  colorEdgesByRelation: true,
  nodeSizeByDegree: false,
  showArtifactThumbs: true,
  curvedEdges: true,
  relationFilter: "",
};

function resolveEdgeStroke(d, vizOptions) {
  if (d.align_mode === "shared") return "#43a047";
  if (d.align_mode === "unique") return "#8d6e63";
  if (vizOptions.colorEdgesByRelation && RELATION_COLOR_MAP[d.relation]) {
    return RELATION_COLOR_MAP[d.relation];
  }
  return "#999";
}

function resolveNodeRadius(d, degreeMap, vizOptions) {
  if (d.role === "shared") return 22;
  const base = Number(d.is_artifact) === 1 ? 25 : 18;
  if (!vizOptions.nodeSizeByDegree) return base;
  const deg = degreeMap.get(String(d.id)) || 1;
  return base + Math.min(deg * 2, 14);
}

export function initGraph(svgEl, fullData, callbacks) {
  const svg = d3.select(svgEl);
  const g = svg.append("g");
  const rect = svgEl.getBoundingClientRect();
  let width = rect.width || 100;
  let height = rect.height || 100;
  let vizOptions = { ...DEFAULT_VIZ_OPTIONS, ...(fullData.vizOptions || {}) };
  let simulation = d3.forceSimulation(fullData.nodes)
     // 修正：显式指定使用 id 字段作为关联键
      .force("link", d3.forceLink(fullData.links).id(d => String(d.id)).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));
  let selectedNodes = [];
  localFullData = fullData;
  const nodeMap = new Map(fullData.nodes.map((n) => [String(n.id), n]));

  // 点击 SVG 背景（非节点/连线）时触发重置
  svg.on("click", (event) => {
    if (event.target === svgEl) {
      // 1. 通知 Vue 清理状态（弹框、选中数组）
      if (callbacks.onClearUI) callbacks.onClearUI();

      // 2. 视觉恢复：移除所有淡化效果
      clearPathHighlightClasses();
      // 恢复默认选中高亮
      g.selectAll(".node").classed("highlight", false);
      // 刷新颜色
      // g.selectAll('.node circle').attr('fill', d => callbacks.getNodeColor(d));
    }
  });

  // 缩放
  const zoom = d3
    .zoom()
    .scaleExtent([0.3, 3])
    .on("zoom", (e) => {
      g.attr("transform", e.transform);
    });
  svg.call(zoom);

  function fitView() {
    try {
      const bounds = g.node()?.getBBox?.();
      if (!bounds?.width || !bounds?.height) return;
      const pad = 48;
      const scale = Math.min(
        3,
        Math.max(
          0.25,
          Math.min(
            (width - pad * 2) / bounds.width,
            (height - pad * 2) / bounds.height
          )
        )
      );
      const tx = width / 2 - scale * (bounds.x + bounds.width / 2);
      const ty = height / 2 - scale * (bounds.y + bounds.height / 2);
      svg.transition().duration(400).call(
        zoom.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      );
    } catch (_) {
      /* ignore */
    }
  }

  // 渲染
  function render(data) {
    g.selectAll("*").remove();

    const compareAlign = isCompareAlignLayout(data);
    const degreeMap = computeDegreeMap(data.links);

    if (compareAlign) {
      clearFixedPositions(data.nodes);
      applyCompareAlignLayout(data.nodes, data.links, width, height);
    } else {
      applyGraphLayout(vizOptions.layoutMode, data.nodes, data.links, width, height, {
        compareAlign: false,
      });
    }

    const pinned = compareAlign || vizOptions.layoutMode !== "force";
    const curved = Boolean(vizOptions.curvedEdges);

    const defs = g.append("defs");
    data.nodes.forEach((n) => {
      if (!vizOptions.showArtifactThumbs || !getThumbUrl(n)) return;
      const r = resolveNodeRadius(n, degreeMap, vizOptions);
      const clipId = `clip-${String(n.id).replace(/[^a-zA-Z0-9_-]/g, "_")}`;
      n._clipId = clipId;
      defs
        .append("clipPath")
        .attr("id", clipId)
        .append("circle")
        .attr("r", r);
    });

    const link = g
      .append("g")
      .attr("class", "links")
      .selectAll("path")
      .data(data.links)
      .join("path")
      .attr("class", "link") // 必须有，否则高亮失效
      .attr("fill", "none")
      .attr("stroke", (d) => resolveEdgeStroke(d, vizOptions))
      .attr("stroke-opacity", (d) => {
        if (!relationMatchesFilter(d, vizOptions.relationFilter)) return 0.08;
        return d.align_mode === "shared" ? 0.9 : 0.6;
      })
      .attr("stroke-width", (d) => (d.align_mode === "shared" ? 2.5 : 1.8))
      .attr("stroke-dasharray", (d) => (d.align_mode === "unique" ? "5 4" : null));

    const linkLabel = g
      .append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(data.links)
      .join("text")
      .attr("class", "link-label") // 必须有
      .text((d) => d.relation)
      .attr("font-size", 10)
      .attr("display", (d) => {
        if (!vizOptions.showLinkLabels) return "none";
        if (!relationMatchesFilter(d, vizOptions.relationFilter)) return "none";
        return null;
      })
      .attr("opacity", (d) => (relationMatchesFilter(d, vizOptions.relationFilter) ? 1 : 0.15));

    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .attr("class", "node") // 必须有，否则 applyHighlightVisuals 找不到目标
      .call(d3.drag().on("start", drag).on("drag", drag).on("end", dragend))
      .on("click", nodeClick); // 统一调用异步的 nodeClick

    node.append("title").text((d) => nodeTooltip(d));

    node
      .append("circle")
      .attr("r", (d) => resolveNodeRadius(d, degreeMap, vizOptions))
      .attr("fill", (d) => {
        if (vizOptions.showArtifactThumbs && getThumbUrl(d)) return "rgba(255,255,255,0.15)";
        return resolveNodeFill(d);
      })
      .attr("stroke", (d) => {
        if (d.role === "shared") return "#2e7d32";
        if (d.role === "unique") return "#6d4c41";
        if (Number(d.is_artifact) === 1) return "rgba(255,255,255,0.85)";
        return "rgba(90,70,50,0.35)";
      })
      .attr("stroke-width", (d) => {
        if (d.role === "shared" || d.role === "unique") return 2;
        return Number(d.is_artifact) === 1 ? 2 : 1;
      });

    node
      .filter((d) => vizOptions.showArtifactThumbs && getThumbUrl(d))
      .append("image")
      .attr("href", (d) => getThumbUrl(d))
      .attr("x", (d) => -resolveNodeRadius(d, degreeMap, vizOptions))
      .attr("y", (d) => -resolveNodeRadius(d, degreeMap, vizOptions))
      .attr("width", (d) => resolveNodeRadius(d, degreeMap, vizOptions) * 2)
      .attr("height", (d) => resolveNodeRadius(d, degreeMap, vizOptions) * 2)
      .attr("clip-path", (d) => (d._clipId ? `url(#${d._clipId})` : null))
      .attr("preserveAspectRatio", "xMidYMid slice");

    node.classed("node-artifact", (d) => Number(d.is_artifact) === 1);
    node.classed("node-non-artifact", (d) => Number(d.is_artifact) !== 1);

    node
      .append("text")
      .text((d) => d.name || d.id)
      .attr("x", (d) => {
        if (Number(d.is_artifact) !== 1) {
          return resolveNodeRadius(d, degreeMap, vizOptions) + 6;
        }
        const nodeText = (d.name || d.id).trim();
        return nodeText.length <= 4 ? 0 : 25;
      })
      .attr("y", (d) => {
        if (Number(d.is_artifact) !== 1) return 4;
        const nodeText = (d.name || d.id).trim();
        return nodeText.length <= 4 ? 3 : 5;
      })
      .attr("text-anchor", (d) => {
        if (Number(d.is_artifact) !== 1) return "start";
        const nodeText = (d.name || d.id).trim();
        return nodeText.length <= 4 ? "middle" : "start";
      })
      .attr("fill", (d) => {
        if (Number(d.is_artifact) !== 1) {
          return DEFAULT_COLORS.otherLabel;
        }
        const nodeText = (d.name || d.id).trim();
        return nodeText.length <= 4 ? "white" : "black";
      })
      .attr("font-size", (d) => {
        const nodeText = (d.name || d.id).trim();
        if (Number(d.is_artifact) === 1 && nodeText.length <= 4) {
          return "12px";
        }
        return "12px";
      });

    node.classed("has-thumb", (d) => Boolean(vizOptions.showArtifactThumbs && getThumbUrl(d)));
    node.classed("has-modality", (d) => Boolean(modalityBadgeText(d)));

    node
      .filter((d) => modalityBadgeText(d))
      .append("text")
      .attr("class", "node-modality-badge")
      .attr("text-anchor", "middle")
      .attr("y", (d) => -resolveNodeRadius(d, degreeMap, vizOptions) - 5)
      .text((d) => modalityBadgeText(d));

    simulation = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3
          .forceLink(data.links)
          .id((d) => String(d.id))
          .distance(compareAlign ? 90 : pinned ? 70 : 120)
      )
      .force("charge", d3.forceManyBody().strength(compareAlign ? -40 : pinned ? -20 : -400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(compareAlign ? 28 : pinned ? 32 : 70));

    simulation.alpha(pinned ? 0.5 : 1).restart();

    simulation.on("tick", () => {
      link.attr("d", (d) => linkPathD(d, curved));
      linkLabel
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2);
      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    applyDefaultVisibility();
    if (pinned) {
      window.setTimeout(() => fitView(), 320);
    }
  }

  // 拖拽
  function drag(e, d) {
    d.fx = e.x;
    d.fy = e.y;
    simulation.alphaTarget(0.3).restart();
  }
  function dragend(e, d) {
    simulation.alphaTarget(0);
    const compareAlign = isCompareAlignLayout(localFullData);
    const keepFixed =
      compareAlign ||
      (vizOptions.layoutMode && vizOptions.layoutMode !== "force");
    if (!keepFixed) {
      d.fx = null;
      d.fy = null;
    }
  }

  // 点击
  async function nodeClick(e, d) {
    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
    if (e.stopPropagation) e.stopPropagation();

    const nodeId = String(d.id);
    // const nodeName = d.name || d.id;
    const isCtrl = e.ctrlKey || e.metaKey; // 是否按住 Ctrl

    // --- 逻辑 A：非文物节点点击 ---
    if (d.is_artifact != 1) {
      if (callbacks.onHandleNonArtifact) {
        // 此时还没拿到数据，我们先传一个空或仅传坐标/基础信息
        callbacks.onHandleNonArtifact(d, e, "PRE_PREPARE");
      }
      const res = await getNonArtifactRelated(nodeId);
      applyHighlightVisuals(res.data);

      const currentNode = res.data.nodes.find((n) => String(n.id) === nodeId);

      // 4. 数据反馈：通知 Vue 展示属性内容
      if (currentNode && callbacks.onHandleNonArtifact) {
        callbacks.onHandleNonArtifact(currentNode, e, "DATA_READY");
      }
      return;
    }

    // // --- 逻辑 B：文物节点选中逻辑 (处理 selectedNodes 数组) ---
    const isAlreadySelected = selectedNodes.includes(nodeId);

    // --- 分支 1：处理“取消选中” (严格复刻你的逻辑) ---
    if (isAlreadySelected) {
      selectedNodes = selectedNodes.filter(id => id !== nodeId);
      await refreshArtifactView(); // 更新视图

      if (callbacks.onNodeSelect) {
        // 传入第三个参数 true，告诉 Vue 这是“取消”动作
        callbacks.onNodeSelect(selectedNodes, d, true);
      }
      return; // 关键：取消后立即返回，不再执行下方“新选中”逻辑
    }

    // --- 分支 2：处理“新选中” ---
    if (!isCtrl) {
      selectedNodes = []; // 未按 Ctrl，清空之前的选中
    }

    if (!selectedNodes.includes(nodeId)) {
      selectedNodes.push(nodeId);
    }
    await refreshArtifactView();

    if (callbacks.onNodeSelect) {
      // 传入 false，告诉 Vue 这是“新增”动作
      callbacks.onNodeSelect(selectedNodes, d, false);
    }
  }

  // 封装原本的 highlightSubgraph 视觉逻辑
  function applyHighlightVisuals(subgraphData) {
    // --- 核心修复：强制统一为字符串 ---
    const ensureId = (node) => {
      // 1. 处理对象情况 (D3 运行后 source/target 会变成对象)
      const rawId = node && typeof node === "object" ? node.id : node;
      // 2. 强制转为字符串，并去掉首尾空格
      return rawId !== undefined && rawId !== null ? String(rawId).trim() : "";
    };

    // 1. 构建子图 ID 集合
    const subgraphNodeIds = new Set(
      subgraphData.nodes.map((n) => ensureId(n.id))
    );

    // 2. 构建子图边的唯一 Key
    const relOf = (link) => link.relation || link.label || "关联";

    const subgraphEdgeKeys = new Set(
      subgraphData.links.map((link) => {
        const sId = ensureId(link.source);
        const tId = ensureId(link.target);
        const sortedIds = [sId, tId].sort();
        return `${sortedIds[0]}-${sortedIds[1]}-${relOf(link)}`;
      })
    );

    // 3. 遍历全图节点：未参与路径的淡化，参与的加强描边
    g.selectAll(".node").each(function (d) {
      const nodeElement = d3.select(this);
      const isIncluded = subgraphNodeIds.has(ensureId(d.id));

      nodeElement.classed("faded", !isIncluded);
      nodeElement.classed("path-highlight", isIncluded);
    });

    // 4. 遍历全图边和标签
    g.selectAll(".link, .link-label").each(function (d) {
      const element = d3.select(this);
      const sId = ensureId(d.source);
      const tId = ensureId(d.target);
      const sortedIds = [sId, tId].sort();
      const dr = d.relation || d.label || "关联";
      const currentEdgeKey = `${sortedIds[0]}-${sortedIds[1]}-${dr}`;

      const isInSubgraph = subgraphEdgeKeys.has(currentEdgeKey);
      element.classed("faded", !isInSubgraph);
      element.classed("path-active", isInSubgraph);
    });
  }

  function clearPathHighlightClasses() {
    g.selectAll(".node").classed("faded", false).classed("path-highlight", false);
    g.selectAll(".link, .link-label").classed("faded", false).classed("path-active", false);
  }

  // 封装你的 updateView 逻辑
  async function refreshArtifactView() {
    if (selectedNodes.length === 0) {
      // 恢复全图：取消所有淡化，恢复 is_artifact === 2 的隐藏状态
      clearPathHighlightClasses();
      g.selectAll(".node").classed("highlight", false)
        .classed("hidden", d => d.is_artifact === 2);
      g.selectAll(".link, .link-label").classed("hidden", d => {
          const s = d.source.id || d.source;
          const t = d.target.id || d.target;
          return isHiddenNode(s) || isHiddenNode(t);
        });
      if (callbacks.onSubgraphUpdate) callbacks.onSubgraphUpdate({ nodes: [], links: [] });
      return;
    }

    // 获取子图数据 (1个点用 two-hop，多个点用 multi-nodes)
    const res = selectedNodes.length === 1
      ? await getTwoHop(selectedNodes[0])
      : await getMultiNodes(selectedNodes.join(','));
    if (callbacks.onSubgraphUpdate) callbacks.onSubgraphUpdate(res.data);

    const relatedIds = new Set(res.data.nodes.map(n => String(n.id)));
    const selectedSet = new Set(selectedNodes.map(String));
    const selectedSingleId = selectedNodes.length === 1 ? String(selectedNodes[0]) : null;

    // 1. 高亮选中的中心点
    g.selectAll(".node").classed("highlight", d => selectedSet.has(String(d.id)));

    // 2. 处理节点显隐与淡化：
    // - 单选文物：隐藏其它文物 + 隐藏所有与其无关的非文物
    // - 多选文物：延续原有行为（非文物未关联则隐藏，其它节点未关联则淡化）
    g.selectAll(".node").each(function(d) {
      const isRelated = relatedIds.has(String(d.id));
      const nodeId = String(d.id);
      const isArtifactNode = d.is_artifact === 1;
      let shouldHide = false;
      let shouldFade = false;

      if (selectedSingleId) {
        shouldHide = isArtifactNode ? nodeId !== selectedSingleId : !isRelated;
        shouldFade = false;
      } else {
        shouldHide = Number(d.is_artifact) === 2 && !isRelated;
        shouldFade = !isRelated;
      }

      d3.select(this)
        .classed("hidden", shouldHide)
        .classed("faded", shouldFade);
    });

    // 3. 处理边和标签：若任一端点被隐藏，边/边标签也隐藏
    g.selectAll(".link, .link-label").each(function(d) {
      const s = String(d.source.id || d.source);
      const t = String(d.target.id || d.target);
      const sourceNode = nodeMap.get(s);
      const targetNode = nodeMap.get(t);
      const sourceRelated = relatedIds.has(s);
      const targetRelated = relatedIds.has(t);

      let sourceHidden = false;
      let targetHidden = false;

      if (selectedSingleId) {
        sourceHidden = sourceNode ? (Number(sourceNode.is_artifact) === 1 ? s !== selectedSingleId : !sourceRelated) : true;
        targetHidden = targetNode ? (Number(targetNode.is_artifact) === 1 ? t !== selectedSingleId : !targetRelated) : true;
      } else {
        sourceHidden = sourceNode ? (Number(sourceNode.is_artifact) === 2 && !sourceRelated) : true;
        targetHidden = targetNode ? (Number(targetNode.is_artifact) === 2 && !targetRelated) : true;
      }

      const isVisible = sourceRelated && targetRelated;
      d3.select(this)
        .classed("hidden", sourceHidden || targetHidden)
        .classed("faded", selectedSingleId ? false : !isVisible);
    });
  }

  function isHiddenNode(id) {
    const node = localFullData.nodes.find(n => n.id === id);
    return node && Number(node.is_artifact) === 2;
  }

  function applyDefaultVisibility() {
    clearPathHighlightClasses();
    g.selectAll(".node")
      .classed("highlight", false)
      .classed("hidden", (d) => Number(d.is_artifact) === 2);

    g.selectAll(".link, .link-label")
      .classed("hidden", (d) => {
        const s = d.source.id || d.source;
        const t = d.target.id || d.target;
        return isHiddenNode(s) || isHiddenNode(t);
      });
  }

  function resetSelection() {
    selectedNodes = []; // 彻底清空 JS 内部的记忆数组
    applyDefaultVisibility();
  }

  // 点击背景的逻辑
  svg.on("click", (event) => {
    if (event.target === svgEl) {
      // 1. 清空 D3 内部变量
      resetSelection();

      // 2. 通知 Vue 清空它的状态
      if (callbacks.onClearUI) {
        callbacks.onClearUI();
      }
    }
  });

  // 启动
  render(fullData);

  /** 退出发现路径高亮：若仍有图谱选中则回到文物/多选视图，否则全图默认显隐 */
  function restoreAfterDiscoveryHighlight() {
    if (selectedNodes.length > 0) {
      void refreshArtifactView();
    } else {
      applyDefaultVisibility();
    }
  }

  function setVizOptions(next) {
    vizOptions = { ...vizOptions, ...next };
    if (localFullData) render(localFullData);
  }

  return {
    reset: () => render(fullData),
    setVizOptions,
    fitView,
    zoom: {
      reset: () => svg.transition().call(zoom.transform, d3.zoomIdentity),
      fit: fitView,
      in: () => svg.transition().call(zoom.scaleBy, 1.3),
      out: () => svg.transition().call(zoom.scaleBy, 0.7),
    },
    toggle: {
      artifacts: (val) => {
        g.selectAll(".node").classed(
          "hidden",
          (d) => !val && d.is_artifact !== 1
        );
      },
      relations: (val) => {
        g.selectAll("text").classed("hidden", !val);
      },
    },
    resetSelection,
    highlightDiscoveryPath(subgraph) {
      if (!subgraph?.nodes?.length) {
        restoreAfterDiscoveryHighlight();
        return;
      }
      applyHighlightVisuals(subgraph);
    },
    clearDiscoveryPath: restoreAfterDiscoveryHighlight,
  };
}
