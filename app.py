import os
import textwrap
from typing import List, Dict, Any, Optional

import requests
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI


# ---------- CONFIG / CLIENTS ----------

def get_ai_client() -> OpenAI:
    """
    Create an OpenAI client for an Azure AI Foundry / Project endpoint.

    Required config (Streamlit secrets OR env vars):
      - OPENAI_BASE_URL  e.g. "https://<something>.services.ai.azure.com/openai/v1"
      - OPENAI_API_KEY   e.g. the key from the Foundry 'Use this model' / 'Connections' blade
    """
    base_url = (
        st.secrets.get("OPENAI_BASE_URL", None)
        or os.getenv("OPENAI_BASE_URL")
    )
    api_key = (
        st.secrets.get("OPENAI_API_KEY", None)
        or os.getenv("OPENAI_API_KEY")
    )

    if not base_url or not api_key:
        st.error(
            "OpenAI configuration missing. "
            "Please set OPENAI_BASE_URL and OPENAI_API_KEY "
            "in Streamlit secrets or environment."
        )
        st.stop()

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    return client


def get_canvas_config() -> tuple[str, str]:
    """Fetch Canvas base URL and API token from secrets/env, or stop if missing."""
    base_url = st.secrets.get("CANVAS_BASE_URL", None) or os.getenv("CANVAS_BASE_URL")
    token = st.secrets.get("CANVAS_API_TOKEN", None) or os.getenv("CANVAS_API_TOKEN")
    if not base_url or not token:
        st.error(
            "Canvas API configuration missing. Please set CANVAS_BASE_URL and "
            "CANVAS_API_TOKEN in Streamlit secrets or environment."
        )
        st.stop()
    return base_url.rstrip("/"), token


# ---------- CANVAS HELPERS ----------

def canvas_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_course(base_url: str, token: str, course_id: str) -> Dict[str, Any]:
    url = f"{base_url}/api/v1/courses/{course_id}"
    resp = requests.get(url, headers=canvas_headers(token))
    resp.raise_for_status()
    return resp.json()


def _paginate_canvas(base_url: str, token: str, url: str, params: Optional[Dict[str, Any]] = None):
    """Generic Canvas pagination helper (not heavily used here, but available)."""
    headers = canvas_headers(token)
    items: List[Any] = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data if isinstance(data, list) else data)
        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
                break
        url = next_url
        params = None  # only on first call
    return items


def get_pages(base_url: str, token: str, course_id: str, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return list of full page objects (with body)."""
    headers = canvas_headers(token)
    items: List[Dict[str, Any]] = []
    url = f"{base_url}/api/v1/courses/{course_id}/pages"
    params = {"per_page": 100}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        for page in resp.json():
            # Need a second call to get full body
            detail_url = f"{base_url}/api/v1/courses/{course_id}/pages/{page['url']}"
            detail_resp = requests.get(detail_url, headers=headers)
            detail_resp.raise_for_status()
            full_page = detail_resp.json()
            items.append(full_page)
            if max_items and len(items) >= max_items:
                return items

        # Pagination – Canvas uses Link header
        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
                break
        url = next_url

    return items


def get_assignments(base_url: str, token: str, course_id: str, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    headers = canvas_headers(token)
    items: List[Dict[str, Any]] = []
    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    params = {"per_page": 100}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data)
        if max_items and len(items) >= max_items:
            return items[:max_items]

        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
                break
        url = next_url

    return items


def get_discussions(base_url: str, token: str, course_id: str, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    headers = canvas_headers(token)
    items: List[Dict[str, Any]] = []
    url = f"{base_url}/api/v1/courses/{course_id}/discussion_topics"
    params = {"per_page": 100}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data)
        if max_items and len(items) >= max_items:
            return items[:max_items]

        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
                break
        url = next_url

    return items


def update_page_html(base_url: str, token: str, course_id: str, url_slug: str, html: str) -> None:
    endpoint = f"{base_url}/api/v1/courses/{course_id}/pages/{url_slug}"
    payload = {"wiki_page": {"body": html}}
    resp = requests.put(endpoint, headers=canvas_headers(token), json=payload)
    resp.raise_for_status()


def update_assignment_html(base_url: str, token: str, course_id: str, assignment_id: int, html: str) -> None:
    endpoint = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"
    payload = {"assignment": {"description": html}}
    resp = requests.put(endpoint, headers=canvas_headers(token), json=payload)
    resp.raise_for_status()


def update_discussion_html(base_url: str, token: str, course_id: str, topic_id: int, html: str) -> None:
    endpoint = f"{base_url}/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
    payload = {"message": html}
    resp = requests.put(endpoint, headers=canvas_headers(token), json=payload)
    resp.raise_for_status()


# ---------- OPENAI HELPERS ----------

def build_rewrite_prompt(
    item: Dict[str, Any],
    model_context: str,
    global_instructions: str,
) -> str:
    """Build a single string prompt for the Responses API."""
    model_context = (model_context or "").strip()
    # Truncate model context for safety
    max_model_chars = 12000
    if len(model_context) > max_model_chars:
        model_context = model_context[:max_model_chars] + "\n\n[Model context truncated for length.]"

    base_rules = textwrap.dedent(
        """
        You are an expert Canvas HTML editor. Preserve links and anchors/IDs

        Requirements:
        - Preserve semantics and learning intent of the original.
        - Follow the policy. Return only HTML, no explanations.
        - Reformat the HTML using DesignPLUS styling.
        - Do not change the written content of the page, only the design.
        - Use Colorado State University branding colors.
        - Use the DesignPLUS theme from the model provided.
        - Place all iframes within DesignPLUS accordions.
        - The focus is on styling, structure, and accessibility — not changing the content.
        """
    )

    item_html = item.get("original_html", "")
    item_type = item.get("type", "page")
    title = item.get("title", "")

    prompt = f"""
    {base_rules}

    ### Global instructions from the user
    {global_instructions or "If no additional instructions, just clean up structure and align with the model course style."}

    ### Model course/style examples
    {model_context}

    ### Target item metadata
    - Type: {item_type}
    - Title: {title}

    ### Original HTML
    {item_html}

    ### Output
    Rewrite the HTML above according to the global instructions and style of the model course.
    Return ONLY the rewritten HTML.
    """.strip()

    return prompt


def rewrite_item(
    client: OpenAI,
    item: Dict[str, Any],
    model_context: str,
    global_instructions: str,
) -> str:
    """
    Call your Azure AI Foundry deployment via the OpenAI client to rewrite a single item.
    Uses Chat Completions API with a single user message containing the prompt.
    """
    prompt = build_rewrite_prompt(item, model_context, global_instructions)

    # Model identifier should be the *deployment name* from Foundry,
    # same value that worked for your dashboard (e.g. "gpt-4.1-dashboard").
    model_name = (
        st.secrets.get("OPENAI_MODEL", None)
        or os.getenv("OPENAI_MODEL")
    )
    if not model_name:
        st.error(
            "OPENAI_MODEL is not set. "
            "Set it to your model deployment name from Azure (Deployment Info → Name)."
        )
        st.stop()

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,  # deterministic; adjust if you want more variation
    )

    out = resp.choices[0].message.content or ""
    return out.strip()



# ---------- STREAMLIT STATE INIT ----------

if "content_items" not in st.session_state:
    st.session_state["content_items"] = []  # list of dicts

if "model_context" not in st.session_state:
    st.session_state["model_context"] = ""

if "course_id" not in st.session_state:
    st.session_state["course_id"] = None

if "rewrite_done" not in st.session_state:
    st.session_state["rewrite_done"] = False


# ---------- UI: SIDEBAR CONFIG ----------

st.set_page_config(page_title="Canvas Course Rewriter", layout="wide")
st.title("Canvas Course Rewriter (Streamlit)")

st.sidebar.header("Canvas connection")

# Only ID is entered by user; base URL + token come from secrets
target_course_id = st.sidebar.text_input(
    "Target course ID",
    help="Numeric ID from the Canvas course URL (e.g. .../courses/205033).",
)

if st.sidebar.button("Fetch course content"):
    if not target_course_id:
        st.sidebar.error("Please provide a target course ID.")
    else:
        base_url, token = get_canvas_config()
        try:
            with st.spinner("Fetching pages, assignments, and discussions from Canvas…"):
                # verify course exists (optional)
                _ = get_course(base_url, token, target_course_id)

                pages = get_pages(base_url, token, target_course_id)
                assignments = get_assignments(base_url, token, target_course_id)
                discussions = get_discussions(base_url, token, target_course_id)

                content_items: List[Dict[str, Any]] = []

                for p in pages:
                    content_items.append(
                        {
                            "type": "page",
                            "id": p["page_id"],   # internal id
                            "canvas_id": p["page_id"],
                            "url_slug": p["url"],
                            "title": p["title"],
                            "original_html": p.get("body", "") or "",
                            "rewritten_html": "",
                            "approved": False,
                        }
                    )

                for a in assignments:
                    content_items.append(
                        {
                            "type": "assignment",
                            "id": a["id"],
                            "canvas_id": a["id"],
                            "title": a["name"],
                            "original_html": a.get("description", "") or "",
                            "rewritten_html": "",
                            "approved": False,
                        }
                    )

                for d in discussions:
                    content_items.append(
                        {
                            "type": "discussion",
                            "id": d["id"],
                            "canvas_id": d["id"],
                            "title": d["title"],
                            "original_html": d.get("message", "") or "",
                            "rewritten_html": "",
                            "approved": False,
                        }
                    )

                st.session_state["content_items"] = content_items
                st.session_state["course_id"] = target_course_id
                st.session_state["rewrite_done"] = False

            st.success(f"Loaded {len(content_items)} items from course {target_course_id}.")

        except Exception as e:
            st.sidebar.error(f"Error fetching content: {e}")


# ---------- STEP 2: MODEL INPUT ----------

st.header("Step 2 – Provide model course/style")

model_source = st.radio(
    "How do you want to provide a model?",
    ["Paste HTML/JSON", "Upload a file", "Use Canvas model course"],
    horizontal=True,
)

if model_source == "Paste HTML/JSON":
    pasted = st.text_area(
        "Paste HTML, JSON, or other structured description of your model course/style:",
        height=200,
        key="pasted_model",
    )
    if st.button("Use this as model"):
        st.session_state["model_context"] = pasted or ""
        st.success("Model context updated from pasted content.")

elif model_source == "Upload a file":
    uploaded = st.file_uploader(
        "Upload an HTML / JSON / TXT file that represents your model course/style.",
        type=["html", "htm", "json", "txt"],
    )
    if uploaded is not None and st.button("Use uploaded file as model"):
        content = uploaded.read().decode("utf-8", errors="ignore")
        st.session_state["model_context"] = content
        st.success("Model context loaded from uploaded file.")

elif model_source == "Use Canvas model course":
    model_course_id = st.text_input(
        "Model course ID (numeric, from Canvas URL)",
        key="model_course_id",
    )
    max_model_items = st.number_input(
        "Max items to pull from model course (total across types)",
        min_value=3,
        max_value=50,
        value=10,
        step=1,
    )
    if st.button("Fetch model course content"):
        if not model_course_id:
            st.error("Model course ID is required.")
        else:
            base_url, token = get_canvas_config()
            try:
                with st.spinner("Fetching model course content…"):
                    # Simple strategy: a few pages, assignments, discussions
                    pages_m = get_pages(base_url, token, model_course_id, max_items=max_model_items)
                    assignments_m = get_assignments(base_url, token, model_course_id, max_items=max_model_items)
                    discussions_m = get_discussions(base_url, token, model_course_id, max_items=max_model_items)

                    model_snippets = []

                    for p in pages_m[:max_model_items]:
                        model_snippets.append(f"### [page] {p['title']}\n{p.get('body', '')}")

                    for a in assignments_m[:max_model_items]:
                        model_snippets.append(f"### [assignment] {a['name']}\n{a.get('description', '')}")

                    for d in discussions_m[:max_model_items]:
                        model_snippets.append(f"### [discussion] {d['title']}\n{d.get('message', '')}")

                    model_context = "\n\n".join(model_snippets)
                    st.session_state["model_context"] = model_context

                st.success("Model context built from Canvas model course.")

            except Exception as e:
                st.error(f"Error fetching model course: {e}")


if st.session_state["model_context"]:
    with st.expander("Preview current model context", expanded=False):
        st.text_area(
            "Model context (trimmed preview):",
            value=st.session_state["model_context"][:4000],
            height=200,
        )


# ---------- STEP 3: CONFIGURE & RUN REWRITE ----------

st.header("Step 3 – Rewrite course content with Azure OpenAI")

global_instructions = st.text_area(
    "High-level rewrite instructions (optional but recommended):",
    placeholder="E.g., Use CSU Online page template, standardize headings, add Outcomes/Instructions/Next Steps sections, etc.",
    height=150,
    key="global_instructions",
)

can_run_rewrite = bool(
    st.session_state["content_items"]
    and st.session_state["model_context"]
)

if st.button("Run rewrite on all items", disabled=not can_run_rewrite):
    client = get_ai_client()
    items = st.session_state["content_items"]
    model_context = st.session_state["model_context"]

    progress = st.progress(0.0)
    status_area = st.empty()

    for idx, item in enumerate(items):
        status_area.write(f"Rewriting [{item['type']}] {item['title']}…")
        try:
            if item.get("original_html"):
                rewritten = rewrite_item(client, item, model_context, global_instructions)
                item["rewritten_html"] = rewritten
            else:
                item["rewritten_html"] = ""
        except Exception as e:
            item["rewrite_error"] = str(e)

        progress.progress((idx + 1) / len(items))

    st.session_state["content_items"] = items
    st.session_state["rewrite_done"] = True
    status_area.write("Rewrite complete.")


# ---------- STEP 4: REVIEW & APPROVAL (VISUAL ONLY) ----------

st.header("Step 4 – Review and approve changes")

items = st.session_state["content_items"]

if not items:
    st.info("Load course content first using the sidebar.")
else:
    for i, item in enumerate(items):
        has_rewrite = bool(item.get("rewritten_html"))
        label = f"[{item['type']}] {item['title']}"
        with st.expander(label, expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Original (visual)")
                if item.get("original_html"):
                    components.html(item["original_html"], height=350, scrolling=True)
                else:
                    st.info("No HTML body for this item.")

            with col2:
                st.subheader("Proposed (visual)")
                if has_rewrite:
                    components.html(item["rewritten_html"], height=350, scrolling=True)
                    st.caption("Proposed version based on model + instructions.")
                else:
                    st.warning("No rewrite available yet. Run the rewrite step above.")

            approved = st.checkbox(
                "Approve this change",
                value=item.get("approved", False),
                key=f"approved_{i}",
            )
            item["approved"] = approved

    # Write back the mutated list
    st.session_state["content_items"] = items

    # Bulk helpers
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Approve ALL items with proposed HTML"):
            for item in st.session_state["content_items"]:
                if item.get("rewritten_html"):
                    item["approved"] = True
            st.success("All items with proposed HTML marked as approved.")

    with col_b:
        if st.button("Clear ALL approvals"):
            for item in st.session_state["content_items"]:
                item["approved"] = False
            st.info("All approvals cleared.")


# ---------- STEP 5: WRITE BACK TO CANVAS ----------

st.header("Step 5 – Write approved changes back to Canvas")

if st.button("Write approved changes to Canvas"):
    if not st.session_state["course_id"]:
        st.error("Target course ID is missing (use the sidebar to load a course).")
    else:
        base_url, token = get_canvas_config()
        course_id = st.session_state["course_id"]
        approved_items = [
            it for it in st.session_state["content_items"]
            if it.get("approved") and it.get("rewritten_html")
        ]

        if not approved_items:
            st.warning("No approved items with rewritten HTML to write back.")
        else:
            with st.spinner(f"Writing {len(approved_items)} items back to Canvas…"):
                errors = []
                for item in approved_items:
                    try:
                        if item["type"] == "page":
                            update_page_html(
                                base_url,
                                token,
                                course_id,
                                item["url_slug"],
                                item["rewritten_html"],
                            )
                        elif item["type"] == "assignment":
                            update_assignment_html(
                                base_url,
                                token,
                                course_id,
                                item["canvas_id"],
                                item["rewritten_html"],
                            )
                        elif item["type"] == "discussion":
                            update_discussion_html(
                                base_url,
                                token,
                                course_id,
                                item["canvas_id"],
                                item["rewritten_html"],
                            )
                    except Exception as e:
                        errors.append((item["title"], str(e)))

            if errors:
                st.error("Some items failed to update:")
                for title, msg in errors:
                    st.write(f"- **{title}**: {msg}")
            else:
                st.success("All approved items successfully written back to Canvas.")
