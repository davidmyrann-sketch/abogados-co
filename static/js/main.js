// Search autocomplete
const searchInput = document.querySelector('input[name="q"]');
if (searchInput) {
    let timeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const q = this.value.trim();
            if (q.length < 2) return;
            fetch(`/api/search-suggest?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => {
                    // Basic autocomplete could be added here
                });
        }, 300);
    });
}
