document.addEventListener("DOMContentLoaded", () => {
    // 1. Dark Mode Toggle Logic
    const toggleBtn = document.getElementById("themeToggle");
    const currentTheme = localStorage.getItem("theme") || "light";
    
    if (currentTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
        if(toggleBtn) toggleBtn.innerHTML = "☀️ Light Mode";
    }

    if(toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            let theme = document.documentElement.getAttribute("data-theme");
            if (theme === "dark") {
                document.documentElement.setAttribute("data-theme", "light");
                localStorage.setItem("theme", "light");
                toggleBtn.innerHTML = "🌙 Dark Mode";
            } else {
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
                toggleBtn.innerHTML = "☀️ Light Mode";
            }
        });
    }

    // 2. Character Counter for Creation Frameworks
    const editor = document.getElementById("blogContentEditor");
    const counter = document.getElementById("charCounter");
    if (editor && counter) {
        editor.addEventListener("input", () => {
            counter.textContent = `${editor.value.length} characters written`;
        });
    }

    // 3. Complete Page Loader Animation Management
    const loader = document.getElementById("loader");
    if(loader) {
        setTimeout(() => { loader.style.display = 'none'; }, 400);
    }

    // 4. Auto-Dismiss Flash Notification Cards
    setTimeout(() => {
        let alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            let bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 4000);

    // 5. Decoupled Click Event Listener for Posts & Interactive Comments Engine
    document.body.addEventListener("click", (event) => {
        // --- Like Handler Engine Component ---
        const likeBtn = event.target.closest(".like-btn");
        if (likeBtn) {
            const postId = likeBtn.getAttribute("data-post-id");
            fetch(`/post/${postId}/like`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(response => {
                if (!response.ok) {
                    alert("Please log in to like posts.");
                    throw new Error("Unauthorized access status encountered");
                }
                return response.json();
            })
            .then(data => {
                if (data.likes !== undefined) {
                    document.getElementById(`like-count-${postId}`).textContent = data.likes;
                }
            })
            .catch(err => console.error(err));
            return;
        }

        // --- Comment Edit Form Toggle Event ---
        const editCommentBtn = event.target.closest(".edit-comment-btn");
        if (editCommentBtn) {
            const commentId = editCommentBtn.getAttribute("data-comment-id");
            document.getElementById(`comment-display-${commentId}`).classList.add("d-none");
            document.getElementById(`comment-edit-form-${commentId}`).classList.remove("d-none");
            return;
        }

        // --- Comment Edit Cancel Event ---
        const cancelCommentBtn = event.target.closest(".cancel-comment-btn");
        if (cancelCommentBtn) {
            const commentId = cancelCommentBtn.getAttribute("data-comment-id");
            document.getElementById(`comment-display-${commentId}`).classList.remove("d-none");
            document.getElementById(`comment-edit-form-${commentId}`).classList.add("d-none");
            return;
        }
    });
});
