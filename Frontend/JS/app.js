async function searchProducts() {
    const productName = document.getElementById('productName').value;
    if (!productName) {
        alert('Vui lòng nhập tên sản phẩm');
        return;
    }

    try {
        console.log('Gửi yêu cầu tìm kiếm:', productName);
        const response = await fetch('http://127.0.0.1:8000/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ product_name: productName }),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Kết quả:', data);
        displayResults(data.results);
    } catch (error) {
        console.error('Lỗi:', error);
        document.getElementById('results').innerHTML = '<p>Đã xảy ra lỗi khi tìm kiếm.</p>';
    }
}

function displayResults(products) {
    const resultsDiv = document.getElementById('results');
    if (!products || products.length === 0) {
        resultsDiv.innerHTML = '<p>Không tìm thấy sản phẩm.</p>';
        return;
    }

    let html = '<table>';
    html += '<tr><th>Tên sản phẩm</th><th>Cửa hàng</th><th>Giá (VNĐ)</th><th>Đánh giá</th><th>Liên kết</th><th>Cập nhật</th></tr>';
    products.forEach(product => {
        html += `<tr>
            <td>${product.name}</td>
            <td>${product.store_name}</td>
            <td>${product.price.toLocaleString()}</td>
            <td>${product.rating || 'N/A'}</td>
            <td><a href="${product.link}" target="_blank">Xem sản phẩm</a></td>
            <td>${new Date(product.updated_at).toLocaleString()}</td>
        </tr>`;
    });
    html += '</table>';
    resultsDiv.innerHTML = html;
}