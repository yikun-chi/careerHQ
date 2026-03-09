const chat = document.getElementById("chat-history");
const zone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");

let careerQuestionsData = [];

function addMsg(html, cls) {
    const d = document.createElement("div");
    d.className = "msg " + cls;
    d.innerHTML = html;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
}

function addCard(html) {
    const d = document.createElement("div");
    d.className = "result-card";
    d.innerHTML = html;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
}

window.addEventListener("DOMContentLoaded", () => {
    addMsg("Welcome to CareerHQ! Upload your resume to discover your top skills, abilities, and work values.", "bot");
});

zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

zone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
    // Clean restart: clear previous results
    chat.innerHTML = "";
    careerQuestionsData = [];
    addMsg("Welcome to CareerHQ! Upload your resume to discover your top skills, abilities, and work values.", "bot");

    addMsg("Uploaded: " + file.name, "user");

    const spinnerMsg = addMsg('<span class="spinner"></span> Analyzing <b>' + escHtml(file.name) + '</b>... This takes 30-60 seconds.', "bot");

    zone.style.pointerEvents = "none";
    zone.style.opacity = "0.5";

    const form = new FormData();
    form.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: form });
        spinnerMsg.remove();

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            addMsg("Error: " + (err.detail || "Upload failed"), "bot error-msg");
            zone.style.pointerEvents = "";
            zone.style.opacity = "";
            return;
        }

        const data = await res.json();
        renderResults(data);
    } catch (e) {
        spinnerMsg.remove();
        addMsg("Network error: " + e.message, "bot error-msg");
        zone.style.pointerEvents = "";
        zone.style.opacity = "";
    }
}


function enforceMaxSelections(inputName, maxSelections) {
    const checkboxes = Array.from(document.querySelectorAll(`input[name="${inputName}"][type="checkbox"]`));
    const checked = checkboxes.filter(c => c.checked);
    const disableUnchecked = checked.length >= maxSelections;

    for (const cb of checkboxes) {
        if (!cb.checked) cb.disabled = disableUnchecked;
        else cb.disabled = false;
    }
}

function collectQuestionnaireAnswers() {
    return careerQuestionsData.map(q => {
        const checked = Array.from(document.querySelectorAll(`input[name="question-${q.id}"]:checked`));
        if (!checked.length) return null;
        const answer = checked.map(el => el.value).join(", ");
        return { question: q.prompt, answer };
    }).filter(Boolean);
}

function renderResults(data) {
    if (data.jobs && data.jobs.length) {
        let html = "<h3>Work Experience</h3>";
        for (const j of data.jobs) {
            html += '<div class="job-entry">';
            html += '<div class="title">' + escHtml(j.job_title) + "</div>";
            html += '<div class="meta">' + escHtml(j.company) + " &middot; " + escHtml(j.occupation) + " &middot; " + j.years + " yr</div>";
            html += "</div>";
        }
        addCard(html);
    }

    if (data.education && data.education.length) {
        let html = "<h3>Education</h3>";
        for (const e of data.education) {
            html += '<div class="edu-entry">';
            html += '<div class="title">' + escHtml(e.institution) + "</div>";
            const parts = [e.degree, e.field, e.year].filter(Boolean);
            if (parts.length) html += '<div class="meta">' + escHtml(parts.join(" - ")) + "</div>";
            html += "</div>";
        }
        addCard(html);
    }

    if (data.resume_skills && data.resume_skills.length) {
        let html = "<h3>Skills from Resume</h3><div class='skills-list'>";
        for (const s of data.resume_skills) html += '<span class="skill-pill">' + escHtml(s) + "</span>";
        html += "</div>";
        addCard(html);
    }

    if (data.attribute_sections) {
        let html = '<h3>Profile Attributes <span class="edit-hint">(click scores to edit)</span></h3>';
        for (const section of data.attribute_sections) {
            if (!section.attributes.length) continue;
            html += '<div class="attr-section">';
            html += '<div class="section-title">' + escHtml(section.label) + "</div>";
            for (const a of section.attributes) {
                const pct = Math.min(100, a.capability);
                html += '<div class="attr-bar">';
                html += '<span class="name" title="' + escAttr(a.description || a.attribute_id) + '">' + escHtml(a.name) + "</span>";
                html += '<div class="bar-bg"><div class="bar-fill" style="width:' + pct + '%"></div></div>';
                html += '<span class="value editable-value" data-attr-id="' + escAttr(a.attribute_id) + '">' + a.capability + "</span>";
                html += "</div>";
            }
            html += "</div>";
        }
        const card = addCard(html);
        card.addEventListener("click", handleAttributeEdit);
    }

    // Store career questions for later use but don't render them yet
    if (data.career_questions && data.career_questions.length) {
        careerQuestionsData = data.career_questions;
    }

    addMsg(
        'Profile complete! Review and edit your attribute scores above, then generate career matches.<br><br>' +
        '<button class="action-btn" id="run-career-btn">Generate Initial Matching</button>',
        "bot"
    );
    document.getElementById("run-career-btn").addEventListener("click", handleCareerAnalysis);

    zone.style.pointerEvents = "";
    zone.style.opacity = "";
}

function handleAttributeEdit(e) {
    const target = e.target;
    if (!target.classList.contains("editable-value")) return;

    const attrId = target.dataset.attrId;
    const currentValue = parseFloat(target.textContent);

    const input = document.createElement("input");
    input.type = "number";
    input.className = "attr-edit-input";
    input.min = "0";
    input.max = "100";
    input.step = "1";
    input.value = currentValue;

    target.replaceWith(input);
    input.focus();
    input.select();

    function commit() {
        const newValue = Math.max(0, Math.min(100, parseFloat(input.value) || 0));
        const span = document.createElement("span");
        span.className = "value editable-value";
        span.dataset.attrId = attrId;
        span.textContent = newValue;
        input.replaceWith(span);

        // Update bar width
        const barRow = span.closest(".attr-bar");
        if (barRow) {
            const fill = barRow.querySelector(".bar-fill");
            if (fill) fill.style.width = Math.min(100, newValue) + "%";
        }

        // Send update to backend
        fetch("/api/user/attributes/" + encodeURIComponent(attrId), {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ capability: newValue }),
        }).catch(() => {});
    }

    function revert() {
        const span = document.createElement("span");
        span.className = "value editable-value";
        span.dataset.attrId = attrId;
        span.textContent = currentValue;
        input.replaceWith(span);
    }

    input.addEventListener("blur", commit);
    input.addEventListener("keydown", e => {
        if (e.key === "Enter") { input.removeEventListener("blur", commit); commit(); }
        if (e.key === "Escape") { input.removeEventListener("blur", commit); revert(); }
    });
}

async function handleCareerAnalysis() {
    const btn = document.getElementById("run-career-btn");
    if (btn) btn.disabled = true;

    const spinnerMsg = addMsg('<span class="spinner"></span> Finding matching careers...', "bot");

    try {
        const res = await fetch("/api/career-analysis");
        spinnerMsg.remove();

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            addMsg("Error: " + (err.detail || "Career analysis failed"), "bot error-msg");
            return;
        }

        const data = await res.json();
        renderCareerResults(data);

    } catch (e) {
        spinnerMsg.remove();
        addMsg("Network error: " + e.message, "bot error-msg");
    }
}

function renderCareerResults(data) {
    if (!data.matches || !data.matches.length) {
        addMsg("No matching occupations found. Try uploading a more detailed resume.", "bot");
        return;
    }

    let html = "<h3>Career Matches</h3>";

    for (const m of data.matches) {
        const hoverDetails = [
            `Occupation ID: ${m.occupation_id || "N/A"}`,
            `Matched Categories: ${(m.matched_categories || []).join(", ") || "None"}`,
            `Match Score: ${m.match_count}/${m.total_categories}`,
        ].join("\n");

        html += '<div class="career-match">';
        html += '<div class="match-header">';
        html += '<span class="match-name" title="' + escAttr(hoverDetails) + '">' + escHtml(m.occupation_name) + '</span>';
        html += '<span class="match-badge">' + m.match_count + '/' + m.total_categories + '</span>';
        html += '</div>';
        html += '<div class="match-categories">';
        for (const cat of m.matched_categories) {
            html += '<span class="category-pill">' + escHtml(cat) + '</span>';
        }
        html += '</div>';
        html += '</div>';
    }

    addCard(html);
    renderFeedbackPanel();
}

function renderFeedbackPanel() {
    const card = document.createElement("div");
    card.className = "result-card feedback-panel";

    let html = '<h3>Refine Your Results</h3>';
    html += '<label class="feedback-label" for="feedback-text">Tell us more about what you\'re looking for:</label>';
    html += '<textarea class="feedback-textarea" id="feedback-text" placeholder="e.g., I prefer leadership roles with flexible hours, interested in tech industry..."></textarea>';

    if (careerQuestionsData.length) {
        html += '<div class="questions-toggle-section">';
        html += '<button class="secondary-btn" id="toggle-questions-btn">Answer Additional Questions</button>';
        html += '<div id="questionnaire-container" style="display:none;"></div>';
        html += '</div>';
    }

    html += '<div class="feedback-actions">';
    html += '<button class="action-btn" id="get-top3-btn">Get Top 3 Recommendations</button>';
    html += '</div>';

    card.innerHTML = html;
    chat.appendChild(card);
    chat.scrollTop = chat.scrollHeight;

    if (careerQuestionsData.length) {
        document.getElementById("toggle-questions-btn").addEventListener("click", () => {
            const container = document.getElementById("questionnaire-container");
            const btn = document.getElementById("toggle-questions-btn");
            if (container.style.display === "none") {
                container.style.display = "";
                btn.textContent = "Hide Questions";
                if (!container.hasChildNodes()) {
                    renderQuestionnaireInto(container);
                }
            } else {
                container.style.display = "none";
                btn.textContent = "Answer Additional Questions";
            }
        });
    }

    document.getElementById("get-top3-btn").addEventListener("click", handleRefineCareerMatches);
}

function renderQuestionnaireInto(container) {
    careerQuestionsData.forEach((question, index) => {
        const block = document.createElement("div");
        block.className = "question-block";

        const prompt = document.createElement("div");
        prompt.className = "question-prompt";
        prompt.textContent = `${index + 1}. ${question.prompt}`;
        block.appendChild(prompt);

        const optionsWrap = document.createElement("div");
        optionsWrap.className = "question-options";

        const inputType = question.selection === "multi" ? "checkbox" : "radio";
        const inputName = `question-${question.id}`;

        (question.options || []).forEach((option, optionIndex) => {
            const optionLabel = document.createElement("label");
            optionLabel.className = "question-option";

            const optionInput = document.createElement("input");
            optionInput.type = inputType;
            optionInput.name = inputName;
            optionInput.value = option;
            optionInput.id = `${inputName}-${optionIndex}`;

            if (inputType === "checkbox" && question.max_selections) {
                optionInput.dataset.maxSelections = String(question.max_selections);
                optionInput.addEventListener("change", () => enforceMaxSelections(inputName, question.max_selections));
            }

            const optionText = document.createElement("span");
            optionText.textContent = option;

            optionLabel.appendChild(optionInput);
            optionLabel.appendChild(optionText);
            optionsWrap.appendChild(optionLabel);
        });

        block.appendChild(optionsWrap);
        container.appendChild(block);
    });
}

async function handleRefineCareerMatches() {
    const btn = document.getElementById("get-top3-btn");
    if (btn) btn.disabled = true;

    const feedbackEl = document.getElementById("feedback-text");
    const feedback = feedbackEl ? feedbackEl.value.trim() : "";
    const answers = collectQuestionnaireAnswers();

    if (!feedback && !answers.length) {
        addMsg("Please provide some feedback or answer at least one question.", "bot error-msg");
        if (btn) btn.disabled = false;
        return;
    }

    const spinnerMsg = addMsg('<span class="spinner"></span> Re-ranking careers with your preferences...', "bot");

    try {
        const res = await fetch("/api/career-analysis/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers, feedback }),
        });

        spinnerMsg.remove();

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            addMsg("Error: " + (err.detail || "Refinement failed"), "bot error-msg");
            if (btn) btn.disabled = false;
            return;
        }

        const data = await res.json();
        renderRefinedResults(data);
    } catch (e) {
        spinnerMsg.remove();
        addMsg("Network error: " + e.message, "bot error-msg");
        if (btn) btn.disabled = false;
    }
}

function renderRefinedResults(data) {
    if (!data.top_careers || !data.top_careers.length) {
        addMsg("Could not generate refined recommendations. Please try again.", "bot");
        return;
    }

    addMsg("<b>Top 3 Career Recommendations</b>", "bot");
    data.top_careers.forEach((career, index) => {
        const hoverDetails = [
            `Occupation ID: ${career.occupation_id || "N/A"}`,
        ].join("\n");

        let html = '<div class="refined-career">';
        html += '<div class="refined-title" title="' + escAttr(hoverDetails) + '">#' + (index + 1) + ' ' + escHtml(career.occupation_name) + '</div>';
        html += '<div class="refined-reason"><b>Profile fit:</b> ' + escHtml(career.profile_fit) + '</div>';
        html += '<div class="refined-reason"><b>Preference fit:</b> ' + escHtml(career.preference_fit) + '</div>';
        html += '</div>';
        addCard(html);
    });
}

function escHtml(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;");
}

function escAttr(s) {
    return escHtml(s);
}
