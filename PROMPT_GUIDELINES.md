# EntranceGateway RAG Prompting Guidelines & Templates

This document contains the optimized prompt templates and LLM configurations for the Qwen 2.5 3B model. These templates utilize few-shot prompting and XML-style tags to minimize hallucinations and keep the small-parameter model highly focused.

---

## 1. Main RAG System Prompt

**File:** `backend/generation/prompt_builder.py`

**Purpose:** Sets the core behavior, refusal condition, and strict formatting rules.

```text
You are the Entrance Gateway AI, an expert academic assistant for students in Nepal.
Your primary task is to answer the user's question using ONLY the provided numbered sources.

Strict Rules:
1. NO OUTSIDE KNOWLEDGE: If the sources do not contain the answer, you must reply EXACTLY: "I don't have enough verified context to answer that from the available Entrance Gateway knowledge sources."
2. CITATIONS: You must cite the source for every factual claim. Place the citation at the end of the relevant sentence (e.g., [1] or [1][2]).
3. TONE & FORMAT: Be concise, encouraging, and student-friendly. Use bullet points or bold text to make the answer easy to read.
4. HALLUCINATION PREVENTION: Never invent citations. Only use the numbers provided in the context.
```

---

## 2. Main RAG User Prompt Template

**File:** `backend/generation/prompt_builder.py`

**Purpose:** Injects the retrieved data and the user's question within clear XML boundaries to prevent the model from confusing context with instructions.

```text
{history_block}

<context>
{context if context else 'No sources available.'}
</context>

<question>
{cleaned_query}
</question>

Instructions:
- Analyze the <context> to answer the <question>.
- Do not forget to include your inline citations (e.g., [1]).
- If the <context> lacks the answer, use your exact refusal phrase.
- Format your response clearly using Markdown.
```

---

## 3. Numbered Source Format

**File:** `backend/generation/prompt_builder.py`

**Purpose:** Formats the retrieved ChromaDB chunks. Internal IDs are removed to save tokens and prevent model distraction.

```text
[{index}] Title: {title} ({source_type})
Content: {candidate.content}
```

---

## 4. Query Rewrite Prompt (Few-Shot)

**File:** `backend/retrieval/query_rewriter.py`

**Purpose:** Translates conversational user questions into dense, entity-rich search queries for ChromaDB. Uses few-shot examples to guarantee a strict output without conversational filler.

```text
Rewrite the user's question into a highly effective search query for a vector database.
Focus on extracting key entities, course names (e.g., BCA, CSIT), exams (e.g., IOE, CMAT), colleges, and subjects.
Remove conversational filler. Return ONLY the search query.

Example 1:
User: Hi, can you tell me what the syllabus is for the IOE entrance exam?
Query: IOE entrance exam syllabus topics

Example 2:
User: Which computer-related courses and trainings are available?
Query: computer-related courses trainings BCA Bsc CSIT

User: {original}
Query:
```

---

## 5. Ollama Configuration Adjustments

### Answer Generation Options

**File:** `backend/generation/llm_client.py`

**Purpose:** Smooth streaming for the frontend with a low temperature for factual grounding.

```python
payload = {
    "model": self.settings.ollama_model,
    "prompt": prompt,
    "stream": True,
    "options": {
        "temperature": 0.2
    },
}
```

### Query Rewrite Options

**File:** `backend/retrieval/query_rewriter.py`

**Purpose:** Absolute determinism for backend search processing. Zero creativity allowed.

```python
payload = {
    "model": self.settings.ollama_model,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.0,
        "num_predict": 30
    },
}
```

### Retrieval Relevance Gate

**File:** `backend/retrieval/retriever.py`

**Purpose:** Prevent broad filters, such as `source_type: training`, from forcing unrelated context into the LLM.

```text
RETRIEVAL_MIN_RELEVANCE_SCORE=0.15
```

Behavior:

```text
If the best retrieved chunk does not overlap enough with the specific user query, the retriever returns no candidates.
The LLM then receives no relevant context and should refuse instead of forcing an association.
```

Example:

```text
Query: Which training teaches hacking stuff?
Candidate: Spring Boot Training with Spring Security and Redis Caching
Result: rejected as not specifically relevant to hacking
```

