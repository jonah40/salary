document.addEventListener('DOMContentLoaded', function() {
    $(document).ready(function() {
        document.getElementById('addSalaryForm').addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent default form submission

            var formData = {
                employee_id: document.getElementById('employee_id').value,
                year: document.getElementById('year').value,
                month: document.getElementById('month').value,
                base_salary: document.getElementById('base_salary').value || 0,
                bonus: document.getElementById('bonus').value || 0,
                overtime_pay: document.getElementById('overtime_pay').value || 0,
                deductions: document.getElementById('deductions').value || 0,
                insurance: document.getElementById('insurance').value || 0,
                tax: document.getElementById('tax').value || 0
                // remarks: document.getElementById('remarks').value, // Removed as requested
            };

            fetch('/salaries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
                alert(data.message);
                location.reload();
            })
            .catch((error) => {
                console.error('Error:', error);
                alert('Error: ' + error.message);
            });
        });

        // 监听输入变化，实时计算总额
        $('#addSalaryForm input[type="number"]').on('input', calculateTotal);

        function calculateTotal() {
            let total = 0;
            total += parseFloat($('#base_salary').val()) || 0;
            total += parseFloat($('#bonus').val()) || 0;
            total += parseFloat($('#overtime_pay').val()) || 0;
            total -= parseFloat($('#deductions').val()) || 0;
            total -= parseFloat($('#insurance').val()) || 0;
            total -= parseFloat($('#tax').val()) || 0;
            $('#total').val(total.toFixed(2));
        }
    });
});
