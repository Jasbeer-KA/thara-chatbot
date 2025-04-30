    // chat.js - Complete JavaScript for Thara Chat

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// DOM elements
const fileUploadBtn = document.getElementById('file-upload-btn');
const fileInput = document.getElementById('file-input');
const filePreviewContainer = document.getElementById('file-preview-container');
const errorContainer = document.getElementById('error-container');
const submitBtn = document.getElementById('submit-btn');
const questionInput = document.getElementById('question');
const chatForm = document.getElementById('chat-form');
const chatContainer = document.getElementById('chat-container');
const voiceInputBtn = document.getElementById('voice-input-btn');
const speakerBtn = document.getElementById('speaker-btn');
const historyItems = document.querySelectorAll('.history-item');
const newChatBtn = document.getElementById('new-chat-btn');
const sidebar = document.getElementById('sidebar');
const openSidebarBtn = document.getElementById('open-sidebar');
const closeSidebarBtn = document.getElementById('close-sidebar');

// Speech recognition and synthesis
let recognition;
let isRecording = false;
let speechSynthesis = window.speechSynthesis || null;

// Check if browser supports Web Speech API
const isSpeechSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
const isSynthesisSupported = 'speechSynthesis' in window;

// Initialize speech recognition if supported
if (isSpeechSupported) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        questionInput.value = transcript;
        submitBtn.classList.add('active');
        questionInput.placeholder = 'Message Thara Chat...';
    };

    recognition.onerror = function(event) {
        console.error('Speech recognition error', event.error);
        showError('Speech recognition error: ' + event.error);
        voiceInputBtn.classList.remove('recording');
        isRecording = false;
        questionInput.placeholder = 'Message Thara Chat...';
    };

    recognition.onend = function() {
        if (isRecording) {
            recognition.start();
        } else {
            voiceInputBtn.classList.remove('recording');
            questionInput.placeholder = 'Message Thara Chat...';
        }
    };
} else {
    voiceInputBtn.style.display = 'none';
}

// Initialize text-to-speech if supported
if (!isSynthesisSupported) {
    speakerBtn.style.display = 'none';
    document.querySelectorAll('.message-speaker').forEach(btn => {
        btn.style.display = 'none';
    });
}

// Show error message
function showError(message) {
    errorContainer.textContent = message;
    errorContainer.style.display = 'block';
    setTimeout(() => {
        errorContainer.style.display = 'none';
    }, 5000);
}

// Toggle submit button active state based on input
questionInput.addEventListener('input', function() {
    if (this.value.trim() || fileInput.files.length > 0) {
        submitBtn.classList.add('active');
    } else {
        submitBtn.classList.remove('active');
    }
});

// Handle file upload button click
fileUploadBtn.addEventListener('click', function() {
    fileInput.click();
});

// Handle file selection
fileInput.addEventListener('change', function() {
    filePreviewContainer.innerHTML = '';
    errorContainer.style.display = 'none';
    
    if (this.files.length > 0) {
        const file = this.files[0];
        
        // Validate file size (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            showError('File size too large (max 10MB)');
            this.value = '';
            return;
        }
        
        const filePreview = document.createElement('div');
        filePreview.className = 'file-preview';
        
        // Get appropriate icon based on file type
        let fileIcon;
        if (file.type.startsWith('image/')) {
            fileIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
            </svg>`;
        } else if (file.type.includes('pdf')) {
            fileIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <path d="M10 15v2a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1z"></path>
            </svg>`;
        } else if (file.type.includes('word') || file.type.includes('document')) {
            fileIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <path d="M16 13H8"></path>
                <path d="M16 17H8"></path>
                <path d="M10 9H8"></path>
            </svg>`;
        } else {
            fileIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>`;
        }
        
        filePreview.innerHTML = `
            ${fileIcon}
            <span>${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)</span>
            <button class="remove-file-btn" type="button">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;
        
        // Add remove file functionality
        const removeBtn = filePreview.querySelector('.remove-file-btn');
        removeBtn.addEventListener('click', function() {
            fileInput.value = '';
            filePreviewContainer.innerHTML = '';
            if (!questionInput.value.trim()) {
                submitBtn.classList.remove('active');
            }
        });
        
        filePreviewContainer.appendChild(filePreview);
        submitBtn.classList.add('active');
    }
});

// Handle voice input
voiceInputBtn.addEventListener('click', function() {
    if (!isSpeechSupported) {
        showError('Speech recognition not supported in your browser');
        return;
    }
    
    if (isRecording) {
        recognition.stop();
        isRecording = false;
        this.classList.remove('recording');
    } else {
        try {
            recognition.start();
            isRecording = true;
            this.classList.add('recording');
            questionInput.placeholder = 'Listening...';
            
            // Set timeout to stop listening after 10 seconds
            setTimeout(() => {
                if (isRecording) {
                    recognition.stop();
                    isRecording = false;
                    this.classList.remove('recording');
                    questionInput.placeholder = 'Message Thara Chat...';
                }
            }, 10000);
        } catch (error) {
            console.error('Speech recognition error:', error);
            showError('Error starting speech recognition');
            this.classList.remove('recording');
            isRecording = false;
            questionInput.placeholder = 'Message Thara Chat...';
        }
    }
});

// Handle speaker buttons
speakerBtn.addEventListener('click', function() {
    if (!isSynthesisSupported) {
        showError('Text-to-speech not supported in your browser');
        return;
    }
    
    const messages = document.querySelectorAll('.message-content p');
    if (messages.length === 0) return;
    
    const lastBotMessage = Array.from(messages).reverse().find(p => 
        p.closest('.message').querySelector('.bot-avatar')
    );
    
    if (lastBotMessage) {
        speakMessage(lastBotMessage.textContent);
    }
});

document.addEventListener('click', function(e) {
    if (e.target.closest('.message-speaker')) {
        const message = e.target.closest('.message-speaker').dataset.message;
        speakMessage(message);
    }
});

// Function to speak a message
function speakMessage(message) {
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }
    
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;
    
    speechSynthesis.speak(utterance);
}

// Handle form submission
chatForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const question = questionInput.value.trim();
    const file = fileInput.files[0];
    
    // Validate at least one input
    if (!question && !file) {
        showError('Please enter a question or upload a file');
        return;
    }

    // Add loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
    </svg>`;

    // First add the user's message to the chat
    if (question) {
        const userMessage = document.createElement('div');
        userMessage.className = 'message';
        userMessage.innerHTML = `
            <div class="message-avatar user-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </div>
            <div class="message-content">
                <p>${question}</p>
            </div>
        `;
        chatContainer.appendChild(userMessage);
    }

    if (file) {
        const fileMessage = document.createElement('div');
        fileMessage.className = 'message';
        fileMessage.innerHTML = `
            <div class="message-avatar user-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </div>
            <div class="message-content">
                <p>Uploaded file: ${file.name}</p>
            </div>
        `;
        chatContainer.appendChild(fileMessage);
    }

    // Add typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'message';
    typingIndicator.innerHTML = `
        <div class="message-avatar bot-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 0 0-7.743 16.33"></path>
                <path d="M12 2a10 10 0 0 1 7.743 16.33"></path>
                <path d="M8 16l-2-2 2-2"></path>
                <path d="M16 16l2-2-2-2"></path>
            </svg>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(typingIndicator);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Network response was not ok');
            });
        }
        return response.json();
    })
    .then(data => {
        // Remove typing indicator
        const typingIndicators = document.querySelectorAll('.typing-indicator');
        typingIndicators.forEach(indicator => {
            indicator.closest('.message').remove();
        });
        
        if (data.response) {
            // Add the bot's response to the chat
            const botMessage = document.createElement('div');
            botMessage.className = 'message';
            botMessage.innerHTML = `
                <div class="message-avatar bot-avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a10 10 0 0 0-7.743 16.33"></path>
                        <path d="M12 2a10 10 0 0 1 7.743 16.33"></path>
                        <path d="M8 16l-2-2 2-2"></path>
                        <path d="M16 16l2-2-2-2"></path>
                    </svg>
                </div>
                <div class="message-content">
                    <p>${data.response}</p>
                    <button class="message-speaker" data-message="${data.response}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                            <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                        </svg>
                    </button>
                </div>
            `;
            chatContainer.appendChild(botMessage);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Update history in sidebar
            updateChatHistory(question || `Uploaded file: ${file.name}`, data.response);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError(error.message || 'Could not get a response from the server');
    })
    .finally(() => {
        // Reset form and button state
        questionInput.value = '';
        fileInput.value = '';
        filePreviewContainer.innerHTML = '';
        submitBtn.classList.remove('active');
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>`;
    });
});

// Update chat history in sidebar
function updateChatHistory(query, response) {
    const historyContainer = document.getElementById('history-container');
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item active';
    historyItem.dataset.query = query;
    historyItem.dataset.response = response;
    historyItem.textContent = query.length > 30 ? query.substring(0, 27) + '...' : query;
    
    // Remove active class from all items
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add new item at the top
    historyContainer.insertBefore(historyItem, historyContainer.firstChild);
    
    // Add click handler to new item
    historyItem.addEventListener('click', loadHistoryItem);
}

// Load history item into chat
function loadHistoryItem() {
    const query = this.dataset.query;
    const response = this.dataset.response;
    
    // Clear current chat
    while (chatContainer.children.length > 0) {
        chatContainer.removeChild(chatContainer.lastChild);
    }
    
    // Add the selected conversation
    const userMessage = document.createElement('div');
    userMessage.className = 'message';
    userMessage.innerHTML = `
        <div class="message-avatar user-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
        </div>
        <div class="message-content">
            <p>${query}</p>
        </div>
    `;
    chatContainer.appendChild(userMessage);
    
    const botMessage = document.createElement('div');
    botMessage.className = 'message';
    botMessage.innerHTML = `
        <div class="message-avatar bot-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 0 0-7.743 16.33"></path>
                <path d="M12 2a10 10 0 0 1 7.743 16.33"></path>
                <path d="M8 16l-2-2 2-2"></path>
                <path d="M16 16l2-2-2-2"></path>
            </svg>
        </div>
        <div class="message-content">
            <p>${response}</p>
            <button class="message-speaker" data-message="${response}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                </svg>
            </button>
        </div>
    `;
    chatContainer.appendChild(botMessage);
    
    // Update active state
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    this.classList.add('active');
    
    // Update title
    document.querySelector('.chat-title').textContent = 'Chat History';
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Sidebar toggle functionality
openSidebarBtn.addEventListener('click', function() {
    sidebar.classList.add('visible');
});

closeSidebarBtn.addEventListener('click', function() {
    sidebar.classList.remove('visible');
});

// New chat button functionality
newChatBtn.addEventListener('click', function() {
    // Clear the chat container except for the first welcome message
    while (chatContainer.children.length > 1) {
        chatContainer.removeChild(chatContainer.lastChild);
    }
    
    // Clear the form
    questionInput.value = '';
    fileInput.value = '';
    filePreviewContainer.innerHTML = '';
    submitBtn.classList.remove('active');
    
    // Remove active state from history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Update title
    document.querySelector('.chat-title').textContent = 'New Chat';
});

// Add click handlers to existing history items
historyItems.forEach(item => {
    item.addEventListener('click', loadHistoryItem);
});

// Handle window resize for mobile sidebar
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        sidebar.classList.remove('visible');
    }
});
