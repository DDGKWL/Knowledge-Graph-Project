<template>
  <div class="qa-panel">
    <p class="qa-disclaimer">
      基于图谱 RAG 检索生成，仅供参考；研究结论请以源文与部件对照表为准。
    </p>

    <p v-if="!canAsk" class="qa-scope-hint">{{ scopeHint }}</p>
    <p v-else class="qa-scope-label">{{ scopeLabel }}</p>

    <textarea
      v-model="question"
      class="qa-input"
      rows="3"
      :placeholder="placeholder"
      :disabled="loading || !canAsk"
      @keydown.ctrl.enter.prevent="submitQuestion"
    />

    <div class="qa-actions">
      <button
        type="button"
        class="qa-submit"
        :disabled="loading || !canAsk || !question.trim()"
        @click="submitQuestion"
      >
        {{ loading ? "生成中…" : "提问" }}
      </button>
      <button
        v-if="answer || error"
        type="button"
        class="qa-clear"
        :disabled="loading"
        @click="clearAnswer"
      >
        清空
      </button>
    </div>

    <div v-if="error" class="qa-error">{{ error }}</div>
    <div v-if="answer" class="qa-answer">{{ answer }}</div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { postQA } from "@/utils/api";

const props = defineProps({
  /** 问答 scope：1 个 id → /qa，多个 → /multi-qa */
  targetIds: { type: Array, default: () => [] },
  /** 用于展示的范围说明 */
  scopeNames: { type: Array, default: () => [] },
  mode: { type: String, default: "artifact" },
});

const question = ref("");
const answer = ref("");
const error = ref("");
const loading = ref(false);

const canAsk = computed(() => {
  if (props.mode === "compare") {
    return (props.targetIds || []).length >= 2;
  }
  return (props.targetIds || []).length >= 1;
});

const scopeHint = computed(() => {
  if (props.mode === "compare") {
    return "请先在左侧将至少 2 件文物加入比较，再在此提问。";
  }
  return "请先在主图中点击文物节点，或从左侧队列选择一件文物。";
});

const scopeLabel = computed(() => {
  const names = (props.scopeNames || []).filter(Boolean);
  if (names.length) return `当前范围：${names.join("、")}`;
  return `当前范围：${(props.targetIds || []).join("、")}`;
});

const placeholder = computed(() => {
  if (props.mode === "compare") {
    return "例如：这两件琴在形制或铭文上有何异同？";
  }
  return "例如：这件琴的材质与灰胎是什么？";
});

watch(
  () => (props.targetIds || []).join("\u0001"),
  () => {
    question.value = "";
    answer.value = "";
    error.value = "";
  }
);

async function submitQuestion() {
  if (!canAsk.value || loading.value) return;
  const q = question.value.trim();
  if (!q) return;

  loading.value = true;
  error.value = "";
  answer.value = "";

  try {
    const { data } = await postQA(props.targetIds, q);
    answer.value = String(data?.answer || "").trim() || "（未返回内容）";
  } catch (err) {
    answer.value = "";
    error.value =
      err?.response?.data?.error ||
      err?.message ||
      "问答请求失败，请确认后端已启动且 LLM 可用。";
  } finally {
    loading.value = false;
  }
}

function clearAnswer() {
  answer.value = "";
  error.value = "";
}
</script>

<style scoped>
.qa-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  text-align: left;
}

.qa-disclaimer {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: rgba(92, 76, 57, 0.72);
  font-style: italic;
}

.qa-scope-hint,
.qa-scope-label {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
}

.qa-scope-hint {
  color: rgba(140, 100, 70, 0.9);
}

.qa-scope-label {
  color: rgba(72, 58, 42, 0.85);
  font-weight: 600;
}

.qa-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(184, 159, 119, 0.45);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
  min-height: 72px;
  background: rgba(255, 252, 246, 0.95);
  color: var(--text, #3f3427);
  font-family: inherit;
}

.qa-input:disabled {
  opacity: 0.65;
}

.qa-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.qa-submit {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(95, 135, 124, 0.5);
  background: rgba(95, 135, 124, 0.18);
  color: #2f5c52;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.qa-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.qa-clear {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(184, 159, 119, 0.4);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: rgba(92, 76, 57, 0.8);
}

.qa-error {
  font-size: 12px;
  color: #b54a32;
  line-height: 1.45;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(181, 74, 50, 0.08);
}

.qa-answer {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text, #3f3427);
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 252, 246, 0.95);
  border: 1px solid rgba(184, 159, 119, 0.35);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
}
</style>
