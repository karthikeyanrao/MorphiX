console.log("Script loaded");
function upvotePost(resourceId, btn) {
    fetch('/upvote', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({resource_id: resourceId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.upvotes !== undefined) {
            btn.querySelector('.upvote-count').textContent = data.upvotes;
        } else if (data.error) {
            alert(data.error);
        }
    });
}