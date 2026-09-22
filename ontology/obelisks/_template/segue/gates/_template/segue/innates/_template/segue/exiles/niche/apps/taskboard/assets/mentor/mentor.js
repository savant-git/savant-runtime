(() => {
  "use strict";

  const DOCUMENTS = {
    mentor: {
      label: "mentor",
      url: "/api/mentor/document"
    },
    masterplan: {
      label: "masterplan",
      url: "/api/mentor/source/masterplan"
    },
    structure: {
      label: "structure",
      url: "/api/mentor/source/structure"
    }
  };

  const state = {
    document:
      localStorage.getItem(
        "savant.mentor.document"
      ) || "mentor",
    raw: "",
    sections: [],
    activeSection: null,
    selectedContext: null,
    search: "",
    digest: "",
    revision: "unknown",
    controller: null
  };

  const $ = (selector) =>
    document.querySelector(selector);

  const $$ = (selector) =>
    Array.from(
      document.querySelectorAll(selector)
    );

  const elements = {
    grid: $(".mentor-grid"),
    document: $("#document"),
    outline: $("#outline"),
    outlineTree: $("#outlineTree"),
    outlineToggle: $("#outlineToggle"),
    collapseAll: $("#collapseAll"),
    sectionCount: $("#sectionCount"),
    breadcrumb: $("#breadcrumb"),
    search: $("#searchInput"),
    documentName: $("#documentName"),
    revision: $("#revisionValue"),
    digest: $("#digestValue"),
    projection: $("#projectionState"),
    aiToggle: $("#aiToggle"),
    aiPanel: $("#mentorPanel"),
    closeAi: $("#closeAi"),
    conversation: $("#conversation"),
    aiContext: $("#aiContextLabel"),
    clearContext: $("#clearContext"),
    form: $("#mentorForm"),
    input: $("#mentorInput"),
    send: $("#mentorSend"),
    status: $("#mentorStatus"),
    backToTop: $("#backToTop"),
    loadingTemplate: $("#loadingTemplate")
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function slugify(value) {
    return String(value)
      .toLowerCase()
      .trim()
      .replace(/[`*_~]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 100) || "section";
  }

  function uniqueId(base, used) {
    let id = base;
    let index = 2;

    while (used.has(id)) {
      id = `${base}-${index}`;
      index += 1;
    }

    used.add(id);
    return id;
  }

  async function sha256(text) {
    if (
      !window.crypto ||
      !window.crypto.subtle
    ) {
      return "unavailable";
    }

    const bytes =
      new TextEncoder().encode(text);

    const digest =
      await crypto.subtle.digest(
        "SHA-256",
        bytes
      );

    return Array.from(
      new Uint8Array(digest)
    )
      .map((value) =>
        value
          .toString(16)
          .padStart(2, "0")
      )
      .join("");
  }

  function parseRevision(text) {
    const lines =
      text.split(/\r?\n/).slice(0, 80);

    for (const line of lines) {
      const match =
        line.match(
          /\*\*document revision:\*\*\s*`?([^`\n]+)`?/i
        );

      if (match) {
        return match[1].trim();
      }
    }

    return "unknown";
  }

  function parseSections(markdown) {
    const lines = markdown.split(/\r?\n/);
    const sections = [];
    const used = new Set();
    let inFence = false;

    lines.forEach((line, index) => {
      if (/^\s*```/.test(line)) {
        inFence = !inFence;
        return;
      }

      if (inFence) {
        return;
      }

      const match =
        line.match(
          /^(#{1,6})\s+(.+?)\s*$/
        );

      if (!match) {
        return;
      }

      const level = match[1].length;
      const title = match[2]
        .replace(/\s+#+\s*$/, "")
        .trim();

      const id = uniqueId(
        slugify(title),
        used
      );

      sections.push({
        id,
        level,
        title,
        line: index,
        endLine: lines.length
      });
    });

    for (
      let index = 0;
      index < sections.length;
      index += 1
    ) {
      const current = sections[index];

      for (
        let next = index + 1;
        next < sections.length;
        next += 1
      ) {
        if (
          sections[next].level <=
          current.level
        ) {
          current.endLine =
            sections[next].line;
          break;
        }
      }
    }

    return sections;
  }

  function inlineMarkdown(value) {
    let output = escapeHtml(value);

    output = output.replace(
      /`([^`]+)`/g,
      "<code>$1</code>"
    );

    output = output.replace(
      /\*\*([^*]+)\*\*/g,
      "<strong>$1</strong>"
    );

    output = output.replace(
      /__([^_]+)__/g,
      "<strong>$1</strong>"
    );

    output = output.replace(
      /(?<!\*)\*([^*\n]+)\*(?!\*)/g,
      "<em>$1</em>"
    );

    output = output.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      (
        _match,
        label,
        href
      ) => {
        const safeHref =
          String(href).trim();

        if (
          !/^(https?:|mailto:|#|\/)/i
            .test(safeHref)
        ) {
          return label;
        }

        return (
          `<a href="${escapeHtml(
            safeHref
          )}" ` +
          `rel="noopener noreferrer">` +
          `${label}</a>`
        );
      }
    );

    return output;
  }

  function renderTable(lines) {
    const rows = lines.map((line) =>
      line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim())
    );

    if (rows.length < 2) {
      return null;
    }

    const separator = rows[1];

    const validSeparator =
      separator.every((cell) =>
        /^:?-{3,}:?$/.test(cell)
      );

    if (!validSeparator) {
      return null;
    }

    const header = rows[0];
    const body = rows.slice(2);

    return (
      '<div class="table-wrap">' +
      "<table><thead><tr>" +
      header
        .map(
          (cell) =>
            `<th>${inlineMarkdown(
              cell
            )}</th>`
        )
        .join("") +
      "</tr></thead><tbody>" +
      body
        .map(
          (row) =>
            "<tr>" +
            header
              .map(
                (_cell, index) =>
                  `<td>${inlineMarkdown(
                    row[index] || ""
                  )}</td>`
              )
              .join("") +
            "</tr>"
        )
        .join("") +
      "</tbody></table></div>"
    );
  }

  function renderMarkdown(markdown) {
    const lines = markdown.split(/\r?\n/);
    const sectionByLine = new Map(
      state.sections.map((section) => [
        section.line,
        section
      ])
    );

    const output = [];
    let index = 0;
    let paragraph = [];
    let listType = null;
    let listItems = [];
    let blockquote = [];
    let inFence = false;
    let fenceLanguage = "";
    let fenceLines = [];

    function flushParagraph() {
      if (!paragraph.length) {
        return;
      }

      output.push(
        `<p>${inlineMarkdown(
          paragraph.join(" ")
        )}</p>`
      );

      paragraph = [];
    }

    function flushList() {
      if (!listItems.length) {
        listType = null;
        return;
      }

      const tag =
        listType === "ol"
          ? "ol"
          : "ul";

      output.push(
        `<${tag}>` +
        listItems
          .map(
            (item) =>
              `<li>${inlineMarkdown(
                item
              )}</li>`
          )
          .join("") +
        `</${tag}>`
      );

      listItems = [];
      listType = null;
    }

    function flushQuote() {
      if (!blockquote.length) {
        return;
      }

      output.push(
        "<blockquote><p>" +
        inlineMarkdown(
          blockquote.join(" ")
        ) +
        "</p></blockquote>"
      );

      blockquote = [];
    }

    function flushFence() {
      if (!fenceLines.length) {
        output.push(
          `<pre><code class="language-${escapeHtml(
            fenceLanguage
          )}"></code></pre>`
        );
      } else {
        output.push(
          `<pre><code class="language-${escapeHtml(
            fenceLanguage
          )}">${escapeHtml(
            fenceLines.join("\n")
          )}</code></pre>`
        );
      }

      fenceLines = [];
      fenceLanguage = "";
    }

    while (index < lines.length) {
      const line = lines[index];

      const fence =
        line.match(
          /^\s*```(.*)$/
        );

      if (fence) {
        flushParagraph();
        flushList();
        flushQuote();

        if (!inFence) {
          inFence = true;
          fenceLanguage =
            fence[1].trim();
        } else {
          inFence = false;
          flushFence();
        }

        index += 1;
        continue;
      }

      if (inFence) {
        fenceLines.push(line);
        index += 1;
        continue;
      }

      const section =
        sectionByLine.get(index);

      if (section) {
        flushParagraph();
        flushList();
        flushQuote();

        const tools =
          section.level === 2 ||
          section.level === 3
            ? (
              '<span class="section-tools">' +
              `<button type="button" ` +
              `data-ask-section="${escapeHtml(
                section.id
              )}">ask mentor</button>` +
              "</span>"
            )
            : "";

        output.push(
          `<h${section.level} ` +
          `id="${escapeHtml(
            section.id
          )}" ` +
          `data-section-id="${escapeHtml(
            section.id
          )}">` +
          `${inlineMarkdown(
            section.title
          )}${tools}` +
          `</h${section.level}>`
        );

        index += 1;
        continue;
      }

      if (
        /^\s*\|/.test(line) &&
        index + 1 < lines.length &&
        /^\s*\|/.test(lines[index + 1])
      ) {
        flushParagraph();
        flushList();
        flushQuote();

        const tableLines = [];

        while (
          index < lines.length &&
          /^\s*\|/.test(lines[index])
        ) {
          tableLines.push(lines[index]);
          index += 1;
        }

        const table =
          renderTable(tableLines);

        if (table) {
          output.push(table);
        } else {
          paragraph.push(
            ...tableLines
          );
        }

        continue;
      }

      const quote =
        line.match(
          /^\s*>\s?(.*)$/
        );

      if (quote) {
        flushParagraph();
        flushList();
        blockquote.push(quote[1]);
        index += 1;
        continue;
      }

      if (blockquote.length) {
        flushQuote();
      }

      const unordered =
        line.match(
          /^\s*[-*+]\s+(.+)$/
        );

      if (unordered) {
        flushParagraph();

        if (
          listType &&
          listType !== "ul"
        ) {
          flushList();
        }

        listType = "ul";
        listItems.push(
          unordered[1]
        );

        index += 1;
        continue;
      }

      const ordered =
        line.match(
          /^\s*\d+[.)]\s+(.+)$/
        );

      if (ordered) {
        flushParagraph();

        if (
          listType &&
          listType !== "ol"
        ) {
          flushList();
        }

        listType = "ol";
        listItems.push(
          ordered[1]
        );

        index += 1;
        continue;
      }

      if (listItems.length) {
        flushList();
      }

      if (/^\s*---+\s*$/.test(line)) {
        flushParagraph();
        output.push("<hr>");
        index += 1;
        continue;
      }

      if (!line.trim()) {
        flushParagraph();
        index += 1;
        continue;
      }

      paragraph.push(
        line.trim()
      );

      index += 1;
    }

    flushParagraph();
    flushList();
    flushQuote();

    if (inFence) {
      flushFence();
    }

    return output.join("\n");
  }

  function sectionContext(section) {
    if (!section) {
      return "";
    }

    const lines =
      state.raw.split(/\r?\n/);

    return lines
      .slice(
        section.line,
        section.endLine
      )
      .join("\n")
      .trim();
  }

  function renderOutline() {
    elements.outlineTree.innerHTML = "";

    state.sections.forEach(
      (section, index) => {
        const wrapper =
          document.createElement("div");

        wrapper.className =
          "outline-node";

        wrapper.style.setProperty(
          "--depth",
          Math.max(
            0,
            section.level - 1
          )
        );

        const button =
          document.createElement(
            "button"
          );

        button.type = "button";
        button.className =
          "outline-link";
        button.dataset.target =
          section.id;
        button.dataset.level =
          String(section.level);

        button.innerHTML =
          `<span class="marker">` +
          `${String(
            index + 1
          ).padStart(2, "0")}` +
          `</span>` +
          `<span>${escapeHtml(
            section.title
          )}</span>`;

        button.addEventListener(
          "click",
          () => {
            navigateToSection(
              section.id,
              true
            );

            if (
              window.innerWidth <=
              760
            ) {
              document.body
                .classList.remove(
                  "outline-open"
                );
            }
          }
        );

        wrapper.appendChild(button);
        elements.outlineTree
          .appendChild(wrapper);
      }
    );

    elements.sectionCount.textContent =
      `${state.sections.length} ` +
      (
        state.sections.length === 1
          ? "section"
          : "sections"
      );
  }

  function updateActiveOutline(id) {
    $$(".outline-link").forEach(
      (button) => {
        button.classList.toggle(
          "active",
          button.dataset.target === id
        );
      }
    );
  }

  function parentPath(section) {
    if (!section) {
      return [];
    }

    const index =
      state.sections.indexOf(section);

    const parents = [];
    let wanted =
      section.level - 1;

    for (
      let cursor = index - 1;
      cursor >= 0 && wanted >= 1;
      cursor -= 1
    ) {
      const candidate =
        state.sections[cursor];

      if (
        candidate.level === wanted
      ) {
        parents.unshift(candidate);
        wanted -= 1;
      }
    }

    return [...parents, section];
  }

  function renderBreadcrumb(section) {
    elements.breadcrumb.innerHTML = "";

    if (!section) {
      elements.breadcrumb.textContent =
        DOCUMENTS[state.document]
          ?.label || state.document;
      return;
    }

    const path =
      parentPath(section);

    path.forEach(
      (entry, index) => {
        if (index > 0) {
          const separator =
            document.createElement(
              "span"
            );
          separator.textContent = "/";
          elements.breadcrumb
            .appendChild(separator);
        }

        const button =
          document.createElement(
            "button"
          );

        button.type = "button";
        button.textContent =
          entry.title;

        button.addEventListener(
          "click",
          () =>
            navigateToSection(
              entry.id,
              true
            )
        );

        elements.breadcrumb
          .appendChild(button);
      }
    );
  }

  function setActiveSection(section) {
    state.activeSection =
      section || null;

    updateActiveOutline(
      section?.id || ""
    );

    renderBreadcrumb(section);
  }

  function navigateToSection(
    id,
    updateHash = false
  ) {
    const target =
      document.getElementById(id);

    const section =
      state.sections.find(
        (entry) => entry.id === id
      );

    if (!target || !section) {
      return;
    }

    setActiveSection(section);

    target.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });

    if (updateHash) {
      history.replaceState(
        null,
        "",
        `#${encodeURIComponent(id)}`
      );
    }
  }

  function applySearch() {
    const query =
      state.search.trim();

    const text =
      renderMarkdown(state.raw);

    if (!query) {
      elements.document.innerHTML =
        text;
      bindSectionTools();
      return;
    }

    elements.document.innerHTML =
      text;

    const walker =
      document.createTreeWalker(
        elements.document,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode(node) {
            if (
              !node.nodeValue ||
              !node.nodeValue
                .toLowerCase()
                .includes(
                  query.toLowerCase()
                )
            ) {
              return (
                NodeFilter
                  .FILTER_REJECT
              );
            }

            if (
              node.parentElement &&
              ["SCRIPT", "STYLE", "CODE"]
                .includes(
                  node.parentElement
                    .tagName
                )
            ) {
              return (
                NodeFilter
                  .FILTER_REJECT
              );
            }

            return (
              NodeFilter
                .FILTER_ACCEPT
            );
          }
        }
      );

    const matches = [];

    while (walker.nextNode()) {
      matches.push(
        walker.currentNode
      );
    }

    const expression =
      new RegExp(
        `(${query.replace(
          /[.*+?^${}()|[\]\\]/g,
          "\\$&"
        )})`,
        "gi"
      );

    matches.forEach((node) => {
      const fragment =
        document.createDocumentFragment();

      const parts =
        node.nodeValue.split(
          expression
        );

      parts.forEach((part) => {
        if (
          part.toLowerCase() ===
          query.toLowerCase()
        ) {
          const mark =
            document.createElement(
              "mark"
            );
          mark.textContent = part;
          fragment.appendChild(mark);
        } else {
          fragment.appendChild(
            document.createTextNode(
              part
            )
          );
        }
      });

      node.parentNode.replaceChild(
        fragment,
        node
      );
    });

    bindSectionTools();

    const first =
      elements.document
        .querySelector("mark");

    if (first) {
      first.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    }
  }

  function bindSectionTools() {
    $$("[data-ask-section]")
      .forEach((button) => {
        button.addEventListener(
          "click",
          (event) => {
            event.stopPropagation();

            const section =
              state.sections.find(
                (entry) =>
                  entry.id ===
                  button.dataset
                    .askSection
              );

            if (!section) {
              return;
            }

            selectAiContext(section);
            openAi();
            elements.input.focus();
          }
        );
      });
  }

  function selectAiContext(section) {
    state.selectedContext =
      section || null;

    elements.aiContext.textContent =
      section
        ? section.title
        : `whole ${state.document}`;
  }

  function openAi() {
    elements.aiPanel.hidden = false;
    elements.grid.classList.add(
      "ai-open"
    );
  }

  function closeAi() {
    elements.aiPanel.hidden = true;
    elements.grid.classList.remove(
      "ai-open"
    );
  }

  function appendMessage(
    role,
    text,
    kind = ""
  ) {
    const message =
      document.createElement("div");

    message.className =
      `message ${role} ${kind}`
        .trim();

    const label =
      document.createElement("span");

    label.textContent =
      role === "user"
        ? "you"
        : "mentor";

    const body =
      document.createElement("p");

    body.textContent = text;

    message.append(
      label,
      body
    );

    elements.conversation
      .appendChild(message);

    elements.conversation.scrollTop =
      elements.conversation
        .scrollHeight;

    return message;
  }

  async function askMentor(question) {
    const section =
      state.selectedContext;

    const context =
      section
        ? sectionContext(section)
        : state.raw.slice(
            0,
            14000
          );

    appendMessage(
      "user",
      question
    );

    elements.send.disabled = true;
    elements.input.disabled = true;
    elements.status.textContent =
      "thinking";

    try {
      const response =
        await fetch(
          "/api/mentor/chat",
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
              question,
              document:
                state.document,
              revision:
                state.revision,
              section_id:
                section?.id || null,
              section_title:
                section?.title || null,
              context
            })
          }
        );

      const payload =
        await response.json();

      if (
        !response.ok ||
        !payload.ok
      ) {
        throw new Error(
          payload.error ||
          `mentor request failed: ` +
          `${response.status}`
        );
      }

      appendMessage(
        "assistant",
        payload.response ||
        payload.answer ||
        "Mentor returned no text."
      );

      elements.status.textContent =
        payload.route ||
        "niche → palaver → opus";
    } catch (error) {
      appendMessage(
        "assistant",
        error instanceof Error
          ? error.message
          : String(error),
        "error"
      );

      elements.status.textContent =
        "mentor unavailable";
    } finally {
      elements.send.disabled = false;
      elements.input.disabled = false;
      elements.input.focus();
    }
  }

  function updateDocumentTabs() {
    $$(".doc-tab").forEach(
      (button) => {
        const active =
          button.dataset.document ===
          state.document;

        button.classList.toggle(
          "active",
          active
        );

        button.setAttribute(
          "aria-selected",
          active
            ? "true"
            : "false"
        );
      }
    );
  }

  async function loadDocument(kind) {
    if (!DOCUMENTS[kind]) {
      kind = "mentor";
    }

    state.document = kind;

    localStorage.setItem(
      "savant.mentor.document",
      kind
    );

    updateDocumentTabs();

    elements.documentName
      .textContent =
      DOCUMENTS[kind].label;

    elements.document.innerHTML = "";

    if (
      elements.loadingTemplate
    ) {
      elements.document.appendChild(
        elements.loadingTemplate
          .content.cloneNode(true)
      );
    }

    if (state.controller) {
      state.controller.abort();
    }

    state.controller =
      new AbortController();

    try {
      const response =
        await fetch(
          DOCUMENTS[kind].url,
          {
            cache: "no-store",
            signal:
              state.controller.signal
          }
        );

      if (!response.ok) {
        throw new Error(
          `document request failed: ` +
          `${response.status}`
        );
      }

      const payload =
        await response.json();

      if (!payload.ok) {
        throw new Error(
          payload.error ||
          "mentor document unavailable"
        );
      }

      const text =
        String(
          payload.document || ""
        );

      state.raw = text;
      state.sections =
        parseSections(text);

      state.revision =
        payload.revision ||
        parseRevision(text);

      state.digest =
        payload.sha256 ||
        await sha256(text);

      elements.revision
        .textContent =
        state.revision;

      elements.digest
        .textContent =
        state.digest ===
        "unavailable"
          ? "unavailable"
          : state.digest.slice(
              0,
              12
            );

      elements.digest.title =
        state.digest;

      elements.projection
        .textContent =
        payload.authority_effect ===
        "none"
          ? "non-authoritative"
          : String(
              payload.authority_effect
            );

      elements.document.innerHTML =
        renderMarkdown(text);

      renderOutline();
      bindSectionTools();

      selectAiContext(null);
      setActiveSection(null);

      const hash =
        decodeURIComponent(
          window.location.hash
            .replace(/^#/, "")
        );

      if (
        hash &&
        document.getElementById(hash)
      ) {
        requestAnimationFrame(
          () =>
            navigateToSection(
              hash,
              false
            )
        );
      }
    } catch (error) {
      if (
        error?.name ===
        "AbortError"
      ) {
        return;
      }

      elements.document.innerHTML =
        `<div class="loading-state">` +
        `<strong>mentor projection unavailable</strong>` +
        `<span>${escapeHtml(
          error instanceof Error
            ? error.message
            : String(error)
        )}</span>` +
        `</div>`;
    }
  }

  function observeSections() {
    const observer =
      new IntersectionObserver(
        (entries) => {
          const visible =
            entries
              .filter(
                (entry) =>
                  entry.isIntersecting
              )
              .sort(
                (a, b) =>
                  a.boundingClientRect
                    .top -
                  b.boundingClientRect
                    .top
              );

          if (!visible.length) {
            return;
          }

          const id =
            visible[0].target.id;

          const section =
            state.sections.find(
              (entry) =>
                entry.id === id
            );

          if (section) {
            setActiveSection(
              section
            );
          }
        },
        {
          rootMargin:
            "-150px 0px -70% 0px",
          threshold: 0
        }
      );

    const mutation =
      new MutationObserver(() => {
        observer.disconnect();

        elements.document
          .querySelectorAll(
            "h1[id],h2[id]," +
            "h3[id],h4[id]," +
            "h5[id],h6[id]"
          )
          .forEach((heading) =>
            observer.observe(heading)
          );
      });

    mutation.observe(
      elements.document,
      {
        childList: true,
        subtree: false
      }
    );

    return {
      observer,
      mutation
    };
  }

  $$(".doc-tab").forEach(
    (button) => {
      button.addEventListener(
        "click",
        () => {
          loadDocument(
            button.dataset.document
          );
        }
      );
    }
  );

  elements.outlineToggle
    ?.addEventListener(
      "click",
      () => {
        if (
          window.innerWidth <=
          760
        ) {
          document.body
            .classList.toggle(
              "outline-open"
            );
          return;
        }

        elements.outline.hidden =
          !elements.outline.hidden;

        elements.grid.style
          .gridTemplateColumns =
          elements.outline.hidden
            ? (
              elements.aiPanel.hidden
                ? "minmax(0,1fr)"
                : (
                  "minmax(0,1fr) " +
                  "minmax(330px,28vw)"
                )
            )
            : "";
      }
    );

  elements.collapseAll
    ?.addEventListener(
      "click",
      () => {
        const links =
          $$(".outline-link");

        const topLevel =
          links.filter(
            (link) =>
              Number(
                link.dataset.level
              ) <= 2
          );

        const showingAll =
          links.every(
            (link) =>
              !link.hidden
          );

        if (showingAll) {
          links.forEach(
            (link) => {
              link.hidden =
                Number(
                  link.dataset.level
                ) > 2;
            }
          );

          elements.collapseAll
            .textContent = "+";
        } else {
          links.forEach(
            (link) => {
              link.hidden = false;
            }
          );

          elements.collapseAll
            .textContent = "−";
        }

        if (!topLevel.length) {
          elements.collapseAll
            .textContent = "−";
        }
      }
    );

  elements.aiToggle
    ?.addEventListener(
      "click",
      () => {
        if (
          elements.aiPanel.hidden
        ) {
          openAi();
          elements.input.focus();
        } else {
          closeAi();
        }
      }
    );

  elements.closeAi
    ?.addEventListener(
      "click",
      closeAi
    );

  elements.clearContext
    ?.addEventListener(
      "click",
      () =>
        selectAiContext(null)
    );

  elements.form
    ?.addEventListener(
      "submit",
      async (event) => {
        event.preventDefault();

        const question =
          elements.input.value
            .trim();

        if (!question) {
          return;
        }

        elements.input.value = "";

        await askMentor(question);
      }
    );

  elements.search
    ?.addEventListener(
      "input",
      () => {
        state.search =
          elements.search.value;

        applySearch();
      }
    );

  document.addEventListener(
    "keydown",
    (event) => {
      const target =
        event.target;

      const typing =
        target instanceof
          HTMLInputElement ||
        target instanceof
          HTMLTextAreaElement ||
        target instanceof
          HTMLSelectElement ||
        target?.isContentEditable;

      if (
        event.key === "/" &&
        !typing
      ) {
        event.preventDefault();
        elements.search.focus();
        return;
      }

      if (
        (
          event.ctrlKey ||
          event.metaKey
        ) &&
        event.key
          .toLowerCase() === "k"
      ) {
        event.preventDefault();
        elements.search.focus();
        elements.search.select();
        return;
      }

      if (event.key === "Escape") {
        if (
          document.body
            .classList.contains(
              "outline-open"
            )
        ) {
          document.body
            .classList.remove(
              "outline-open"
            );
          return;
        }

        if (
          !elements.aiPanel.hidden
        ) {
          closeAi();
          return;
        }

        if (elements.search.value) {
          elements.search.value = "";
          state.search = "";
          applySearch();
        }
      }
    }
  );

  window.addEventListener(
    "scroll",
    () => {
      elements.backToTop.hidden =
        window.scrollY < 700;
    },
    {
      passive: true
    }
  );

  elements.backToTop
    ?.addEventListener(
      "click",
      () => {
        window.scrollTo({
          top: 0,
          behavior: "smooth"
        });
      }
    );

  window.addEventListener(
    "hashchange",
    () => {
      const id =
        decodeURIComponent(
          window.location.hash
            .replace(/^#/, "")
        );

      if (id) {
        navigateToSection(
          id,
          false
        );
      }
    }
  );

  observeSections();

  if (!DOCUMENTS[state.document]) {
    state.document = "mentor";
  }

  loadDocument(state.document);
})();
