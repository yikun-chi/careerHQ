// Objective: browser-side logic for chat, upload, and rendering profile data.
let isFirstMessage = true;

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
    const text = userInput.value.trim();
    if (text) {
        appendMessage(text, 'user');
        userInput.value = '';
        if (isFirstMessage) {
            if (text.toLowerCase() === 'yes') {
                appendMessage('Please update your resume.', 'bot');
                isFirstMessage = false;
            } else if (text.toLowerCase() === 'no') {
                appendMessage('Thank you. Please let me know when you want one.', 'bot');
                isFirstMessage = false;
            } else {
                appendMessage('Please answer with "yes" or "no". Would you like to have a career development roadmap?', 'bot');
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
        appendMessage('Part I: Skill Set.', 'bot');
        appendMessage('After parsing your resume, here are your skills. Please edit it if necessary.', 'bot');
        document.getElementById('skills-editor').style.display = 'block';
    }
});

document.getElementById('save-skills').addEventListener('click', function() {
    const skills = document.getElementById('skills-textarea').value;
    appendMessage('Skills updated: ' + skills, 'bot');
    document.getElementById('skills-editor').style.display = 'none';
});
