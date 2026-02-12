const chat = document.getElementById("chat-history");
const zone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");

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
}

// Greeting
window.addEventListener("DOMContentLoaded", () => {
    addMsg("Welcome to CareerHQ! Upload your resume to discover your top skills, abilities, and work values.", "bot");
});

// Drag-and-drop
zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

// Click to browse
zone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
    addMsg("Uploaded: " + file.name, "user");

    const spinnerMsg = addMsg('<span class="spinner"></span> Analyzing <b>' + escHtml(file.name) + '</b>... This takes 30-60 seconds.', "bot");

    // Disable upload zone
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

function renderResults(data) {
    // Jobs
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

    // Education
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

    // Skills
    if (data.resume_skills && data.resume_skills.length) {
        let html = "<h3>Skills from Resume</h3><div class='skills-list'>";
        for (const s of data.resume_skills) html += '<span class="skill-pill">' + escHtml(s) + "</span>";
        html += "</div>";
        addCard(html);
    }

    // Attribute sections
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

    addMsg(
        'Profile complete! Ready to find careers that match your strengths?<br><br>' +
        '<button class="action-btn" id="run-career-btn">Run Career Analysis</button>',
        "bot"
    );
    document.getElementById("run-career-btn").addEventListener("click", handleCareerAnalysis);

    // Re-enable upload
    const zone2 = document.getElementById("upload-zone");
    zone2.style.pointerEvents = "";
    zone2.style.opacity = "";
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
        html += '<div class="career-match">';
        html += '<div class="match-header">';
        html += '<span class="match-name">' + escHtml(m.occupation_name) + '</span>';
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
}

function escHtml(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escAttr(s) {
    return escHtml(s);
}
