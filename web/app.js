const chat = document.getElementById("chat-history");
const zone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");

let pendingQuestions = [];
const DEFAULT_FOLLOW_UP_QUESTIONS = [
    "What kind of work excites you most?",
    "Do you work better alone or with others?",
    "Do you prefer structure or flexibility in how you work?",
    "Do you prefer to focus on one thing or juggle many?",
    "What industries or causes are you drawn to?",
    "What are your top 2 priorities in a job?",
];

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


function renderCareerQuestionnaire(questions) {
    if (!questions || !questions.length) return;

    const card = document.createElement("div");
    card.className = "result-card";

    const title = document.createElement("h3");
    title.textContent = "Career Preference Questions";
    card.appendChild(title);

    questions.forEach((question, index) => {
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
        card.appendChild(block);
    });

    chat.appendChild(card);
    chat.scrollTop = chat.scrollHeight;
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
        let html = "<h3>Profile Attributes</h3>";
        for (const section of data.attribute_sections) {
            if (!section.attributes.length) continue;
            html += '<div class="attr-section">';
            html += '<div class="section-title">' + escHtml(section.label) + "</div>";
            for (const a of section.attributes) {
                const pct = Math.min(100, a.capability);
                html += '<div class="attr-bar">';
                html += '<span class="name" title="' + escAttr(a.description || a.attribute_id) + '">' + escHtml(a.name) + "</span>";
                html += '<div class="bar-bg"><div class="bar-fill" style="width:' + pct + '%"></div></div>';
                html += '<span class="value">' + a.capability + "</span>";
                html += "</div>";
            }
            html += "</div>";
        }
        addCard(html);
    }

    renderCareerQuestionnaire(data.career_questions || []);

    addMsg(
        'Profile complete! Ready to find careers that match your strengths?<br><br>' +
        '<button class="action-btn" id="run-career-btn">Run Career Analysis</button>',
        "bot"
    );
    document.getElementById("run-career-btn").addEventListener("click", handleCareerAnalysis);

    zone.style.pointerEvents = "";
    zone.style.opacity = "";
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

    const followUpQuestions = Array.isArray(data.follow_up_questions) && data.follow_up_questions.length
        ? data.follow_up_questions
        : DEFAULT_FOLLOW_UP_QUESTIONS;

    if (followUpQuestions.length) {
        pendingQuestions = followUpQuestions;
        renderImproveMatchingPrompt();
    }
}

function renderImproveMatchingPrompt() {
    addMsg(
        'Want to improve matching through user input?<br><br>' +
        '<button class="action-btn" id="show-followup-btn">Improve Matching Through User Input</button>',
        "bot"
    );

    document.getElementById("show-followup-btn").addEventListener("click", () => {
        const btn = document.getElementById("show-followup-btn");
        if (btn) btn.disabled = true;
        renderFollowUpQuestions(pendingQuestions);
    });
}

function renderFollowUpQuestions(questions) {
    let html = '<h3>Quick Preference Questions</h3>';
    html += '<p class="followup-helper">Answer these to improve your top picks.</p>';

    questions.forEach((q, idx) => {
        html += '<label class="followup-label" for="followup-' + idx + '">' + escHtml(q) + '</label>';
        html += '<textarea class="followup-input" id="followup-' + idx + '" rows="2" placeholder="Type your answer..."></textarea>';
    });

    html += '<button class="action-btn" id="refine-career-btn">Improve Top Matches</button>';

    addCard(html);
    document.getElementById("refine-career-btn").addEventListener("click", handleRefineCareerMatches);
}

async function handleRefineCareerMatches() {
    const btn = document.getElementById("refine-career-btn");
    if (btn) btn.disabled = true;

    const answers = pendingQuestions.map((question, idx) => ({
        question,
        answer: document.getElementById("followup-" + idx)?.value?.trim() || "",
    })).filter(item => item.answer);

    if (!answers.length) {
        addMsg("Please answer at least one follow-up question before refining.", "bot error-msg");
        if (btn) btn.disabled = false;
        return;
    }

    const spinnerMsg = addMsg('<span class="spinner"></span> Re-ranking careers with your preferences...', "bot");

    try {
        const res = await fetch("/api/career-analysis/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers }),
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

    let html = "<h3>Improved Top 3 Career Recommendations</h3>";
    data.top_careers.forEach((career, index) => {
        const hoverDetails = [
            `Occupation ID: ${career.occupation_id || "N/A"}`,
            `Why this match improved: ${career.reason || "No additional explanation available."}`,
        ].join("\n");

        html += '<div class="refined-career">';
        html += '<div class="refined-title" title="' + escAttr(hoverDetails) + '">#' + (index + 1) + ' ' + escHtml(career.occupation_name) + '</div>';
        html += '<div class="refined-reason">' + escHtml(career.reason) + '</div>';
        html += '</div>';
    });

    addCard(html);
}

function escHtml(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;");
}

function escAttr(s) {
    return escHtml(s);
}
