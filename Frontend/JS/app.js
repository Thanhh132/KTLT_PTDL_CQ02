
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const productName = document.getElementById('search-input').value;
    if (!productName) return;

    const loading = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const recommendationDiv = document.getElementById('recommendation');
    const priceChart = document.getElementById('priceChart').getContext('2d');
    loading.classList.remove('d-none');
    resultsDiv.innerHTML = '';
    recommendationDiv.classList.add('d-none');
    if (window.priceChartInstance) {
        window.priceChartInstance.destroy();
    }

    try {
        console.log("Sending fetch request to /search with product:", productName); // Debug
        const response = await fetch('http://127.0.0.1:8000/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Request-Method': 'POST' // Thêm để hỗ trợ CORS preflight
            },
            body: JSON.stringify({ product_name: productName })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("Received data:", data); // Debug response
        loading.classList.add('d-none');

        if (data.results.length === 0) {
            resultsDiv.innerHTML = '<p class="text-center">Không tìm thấy sản phẩm nào.</p>';
            return;
        }

        data.results.forEach(result => {
            console.log(`Image URL for ${result.name}: ${result.image_url}`); // Debug image_url
            const imageTag = result.image_url && result.image_url !== ''
                ? `<img src="${result.image_url}" class="card-img-top" alt="${result.name}" style="max-height: 200px; object-fit: contain;" onerror="this.src='https://via.placeholder.com/200?text=No+Image';">`
                : `<img src="https://via.placeholder.com/200?text=No+Image" class="card-img-top" alt="${result.name}" style="max-height: 200px; object-fit: contain;">`;
            const card = `
                <div class="col-md-4 mb-3">
                    <div class="card h-100">
                        ${imageTag}
                        <div class="card-body">
                            <h5 class="card-title">${result.name}</h5>
                            <p class="card-text">
                                <strong>Giá:</strong> ${result.price.toLocaleString()}₫<br>
                                <strong>Cửa hàng:</strong> ${result.store_name}<br>
                                <strong>Danh mục:</strong> ${result.category_id || 'Không xác định'}<br>
                                <strong>Đánh giá:</strong> ${result.rating ? result.rating.toFixed(1) : 'Chưa có'}
                            </p>
                            <a href="${result.link}" class="btn btn-info" target="_blank">Xem chi tiết</a>
                        </div>
                    </div>
                </div>`;
            resultsDiv.innerHTML += card;
        });

        if (data.recommendation) {
            recommendationDiv.classList.remove('d-none');
            recommendationDiv.innerHTML = `
                <strong>Gợi ý tốt nhất:</strong> ${data.recommendation.name} tại ${data.recommendation.store_name} 
                với giá ${data.recommendation.price.toLocaleString()}₫ (Đánh giá: ${data.recommendation.rating ? data.recommendation.rating.toFixed(1) : 'Chưa có'})
            `;
        }

        const prices = data.results.map(result => result.price);
        const stores = data.results.map(result => result.store_name);
        window.priceChartInstance = new Chart(priceChart, {
            type: 'bar',
            data: {
                labels: stores,
                datasets: [{
                    label: 'Giá sản phẩm (VNĐ)',
                    data: prices,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        if (data.errors.length > 0) {
            alert('Có lỗi xảy ra: ' + data.errors.join(', '));
        }
    } catch (error) {
        loading.classList.add('d-none');
        resultsDiv.innerHTML = `<p class="text-center text-danger">Lỗi khi tìm kiếm sản phẩm: ${error.message}</p>`;
        console.error('Error:', error);
    }
});
