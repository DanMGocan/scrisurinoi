// Flash message handling
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

// Form handling
document.addEventListener('DOMContentLoaded', () => {
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                email: loginForm.email.value,
                password: loginForm.password.value
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
                    showAlert('Logged in successfully');
                    window.location.href = '/';
                } else {
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                showAlert('An error occurred', 'error');
            }
        });
    }
    
    // Post creation form
    const postForm = document.getElementById('post-form');
    if (postForm) {
        postForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                title: postForm.title.value,
                content: postForm.content.value,
                post_type: postForm.post_type.value
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
                    showAlert('Post created successfully');
                    window.location.href = `/posts/${data.post_id}`;
                } else {
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                showAlert('An error occurred', 'error');
            }
        });
    }
    
    // Comment form
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const postId = commentForm.dataset.postId;
            const formData = {
                content: commentForm.content.value
            };
            
            try {
                const response = await fetch(`/api/posts/${postId}/comments`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert(`Comment added successfully! You earned ${data.points_awarded} points!`);
                    location.reload();
                } else {
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                showAlert('An error occurred', 'error');
            }
        });
    }
});

// Google Sign-In
function handleGoogleSignIn(response) {
    fetch('/api/auth/google/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            token: response.credential
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert('Logged in successfully with Google');
            window.location.href = '/';
        } else {
            showAlert(data.error, 'error');
        }
    })
    .catch(error => {
        showAlert('An error occurred during Google sign-in', 'error');
    });
}
