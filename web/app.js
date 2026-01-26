// Objective: browser-side logic for chat, upload, and rendering profile data.
let currentStep = 'ask_roadmap';

function appendMessage(text, type) {
    const chatHistory = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + type;
    if (type === 'user') {
        const photo = document.createElement('div');
        photo.className = 'photo';
        photo.textContent = 'U'; // Placeholder for user photo
        messageDiv.appendChild(photo);
    }
    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    messageDiv.appendChild(textSpan);
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

window.addEventListener('DOMContentLoaded', function() {
    appendMessage('Welcome to CareerHQ! You can find your personalized career development advice here by analyzing your Skills, Interests, and Values. Do you want me to help you create a career development roadmap?', 'bot');
});

document.getElementById('send-button').addEventListener('click', function() {
    const userInput = document.getElementById('user-input');
    const text = userInput.value.trim().toLowerCase();
    if (text) {
        appendMessage(userInput.value.trim(), 'user');
        userInput.value = '';
        if (currentStep === 'ask_roadmap') {
            if (text === 'yes') {
                appendMessage('Is your resume up to date?', 'bot');
                currentStep = 'ask_resume_up_to_date';
            } else if (text === 'no') {
                appendMessage('Thank you. Please let me know when you want one.', 'bot');
                currentStep = 'done';
            } else {
                appendMessage('Please answer with "yes" or "no". Would you like to have a career development roadmap?', 'bot');
            }
        } else if (currentStep === 'ask_resume_up_to_date') {
            if (text === 'yes') {
                appendMessage('Great! Since your resume is up to date, we can proceed with your current skills.', 'bot');
                // TODO: Call backend API to get information from existing resume
                appendMessage('Part I: Skill Set.', 'bot');
                appendMessage('Here are your skills. Please edit if necessary.', 'bot');
                document.getElementById('skills-editor').style.display = 'block';
                currentStep = 'skills';
            } else if (text === 'no') {
                appendMessage('Please upload your resume.', 'bot');
                currentStep = 'wait_upload';
            } else {
                appendMessage('Please answer with "yes" or "no". Is your resume up to date?', 'bot');
            }
        }
    }
});

document.getElementById('upload-button').addEventListener('click', function() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (file) {
        appendMessage('Uploaded: ' + file.name, 'bot');
        // TODO: Store the file and send to backend API for processing
        appendMessage('Thank you for updating your resume. Please follow the following steps to continue. ', 'bot');
        // TODO: Call backend API to parse resume and get skills
        appendMessage('Part I: Skill Set.', 'bot');
        appendMessage('After parsing your resume, here are your skills. Please edit it if necessary.', 'bot');
        document.getElementById('skills-editor').style.display = 'block';
        currentStep = 'skills';
    }
});

document.getElementById('save-skills').addEventListener('click', function() {
    const skills = document.getElementById('skills-textarea').value;
    appendMessage('Skills updated: ' + skills, 'bot');
    document.getElementById('skills-editor').style.display = 'none';
});
