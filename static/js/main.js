// Utility function to show modals
function showModal(message, type = 'success') {
    // Create modal container if it doesn't exist
    let modalContainer = document.getElementById('modal-container');
    if (!modalContainer) {
        modalContainer = document.createElement('div');
        modalContainer.id = 'modal-container';
        document.body.appendChild(modalContainer);
    }
    
    // Create overlay
    const overlayId = 'overlay-' + Date.now();
    const overlay = document.createElement('div');
    overlay.id = overlayId;
    overlay.className = 'modal-overlay';
    modalContainer.appendChild(overlay);
    
    // Create modal
    const modalId = 'modal-' + Date.now();
    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = `modal modal-${type}`;
    
    // Determine icon and title based on type
    let icon, title;
    if (type === 'success') {
        icon = 'check-circle';
        title = 'Succes';
    } else if (type === 'warning') {
        icon = 'exclamation-triangle';
        title = 'Atenție';
    } else if (type === 'error') {
        icon = 'exclamation-circle';
        title = 'Eroare';
    } else if (type === 'info') {
        icon = 'info-circle';
        title = 'Informație';
    } else {
        icon = 'info-circle';
        title = 'Notificare';
    }
    
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <i class="fas fa-${icon}"></i>
                <span class="modal-title">${title}</span>
                <button class="modal-close" aria-label="Close">&times;</button>
            </div>
            <div class="modal-body">
                ${message}
            </div>
        </div>
    `;
    
    modalContainer.appendChild(modal);
    
    // Show overlay and modal with animation
    requestAnimationFrame(() => {
        overlay.classList.add('show');
        modal.classList.add('show');
    });
    
    // Add event listener to close button
    modal.querySelector('.modal-close').addEventListener('click', function() {
        closeModal(modalId, overlayId);
    });
    
    // Add event listener to overlay for closing when clicked
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeModal(modalId, overlayId);
        }
    });
    
    // Auto-close after 10 seconds
    setTimeout(() => {
        closeModal(modalId, overlayId);
    }, 10000);
    
    return { modalId, overlayId };
}

// Function to close modal
function closeModal(modalId, overlayId) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById(overlayId);
    
    if (modal) {
        modal.classList.remove('show');
    }
    
    if (overlay) {
        overlay.classList.remove('show');
        // Immediately make the overlay non-interactive
        overlay.style.pointerEvents = 'none';
    }
    
    // Remove elements after animation completes
    setTimeout(() => {
        if (modal) {
            modal.remove();
        }
        if (overlay) {
            overlay.remove();
        }
        
        // Check if this was the last modal, and if so, clean up the container
        const modalContainer = document.getElementById('modal-container');
        if (modalContainer && !modalContainer.hasChildNodes()) {
            modalContainer.remove();
        }
    }, 400); // Wait for animation to complete
}

// Handle form submissions and interactions
document.addEventListener('DOMContentLoaded', function() {
    // Login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value
            };
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showModal('Autentificare reușită!');
                    window.location.href = '/';
                } else {
                    showModal(data.error || 'Autentificare eșuată. Verificați email-ul și parola.', 'error');
                }
            } catch (error) {
                console.error('Error during login:', error);
                showModal('A apărut o eroare la autentificare', 'error');
            }
        });
    }
    
    // Registration form submission
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            if (password !== confirmPassword) {
                showModal('Parolele nu se potrivesc', 'error');
                return;
            }
            
            const formData = {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                password: password
            };
            
            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showModal('Înregistrare reușită! Te rugăm să te autentifici.');
                    window.location.href = '/api/auth/login';
                } else {
                    showModal(data.error || 'A apărut o eroare la înregistrare', 'error');
                }
            } catch (error) {
                console.error('Error during registration:', error);
                showModal('A apărut o eroare la înregistrare', 'error');
            }
        });
    }
    
    // Like functionality is now handled in the individual templates
    
    const postForm = document.getElementById('post-form');
    if (postForm) {
        postForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                title: document.getElementById('title').value,
                description: document.getElementById('description')?.value || '',
                content: document.getElementById('content').value,
                post_type: document.getElementById('post_type').value
            };
            
            try {
                const response = await fetch('/api/posts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showModal('Postare creată cu succes!');
                    window.location.href = `/posts/${data.post_id}`;
                } else {
                    showModal(data.error || 'A apărut o eroare la crearea postării', 'error');
                }
            } catch (error) {
                console.error('Error creating post:', error);
                showModal('A apărut o eroare la crearea postării', 'error');
            }
        });
    }
    
    // Handle comment form submission
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const postId = this.getAttribute('data-post-id');
            const content = document.getElementById('content').value;
            
            try {
                const response = await fetch(`/api/posts/${postId}/comments`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    if (data.warning) {
                        showModal(data.warning, 'warning');
                    } else {
                        showModal(`Comentariu adăugat cu succes! Ai primit ${data.points_awarded} puncte.`);
                    }
                    // Reload the page to show the new comment
                    window.location.reload();
                } else {
                    showModal(data.error || 'A apărut o eroare la adăugarea comentariului', 'error');
                }
            } catch (error) {
                console.error('Error adding comment:', error);
                showModal('A apărut o eroare la adăugarea comentariului', 'error');
            }
        });
    }
});
