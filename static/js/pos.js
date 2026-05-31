/**
 * MediPOS — Point of Sale Cart JavaScript
 *
 * Handles all client-side POS operations: medicine search (debounced),
 * cart add/remove/update via fetch API, barcode scanner support,
 * real-time totals calculation, payment change computation, and
 * hold/resume/clear cart functionality.
 *
 * Depends on Bootstrap 5 (modals, toasts), and the CSRF token
 * provided by Django in the template.
 */
(function () {
    'use strict';

    // ── CSRF Setup ──────────────────────────────────────────────────────
    function getCSRFToken() {
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    const CSRF_TOKEN = getCSRFToken();

    async function fetchJSON(url, options = {}) {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
        };
        const merged = { ...defaults, ...options };
        if (merged.headers) {
            merged.headers = { ...defaults.headers, ...(options.headers || {}) };
        }
        const response = await fetch(url, merged);
        return response.json();
    }

    // ── DOM References ───────────────────────────────────────────────────
    const searchInput = document.getElementById('medicineSearch');
    const barcodeInput = document.getElementById('barcodeInput');
    const productGrid = document.getElementById('productGrid');
    const cartTableBody = document.getElementById('cartTableBody');
    const cartSubtotal = document.getElementById('cartSubtotal');
    const cartDiscount = document.getElementById('cartDiscount');
    const cartTax = document.getElementById('cartTax');
    const cartGrandTotal = document.getElementById('cartGrandTotal');
    const discountType = document.getElementById('discountType');
    const discountValue = document.getElementById('discountValue');
    const paymentMode = document.getElementById('paymentMode');
    const amountPaid = document.getElementById('amountPaid');
    const changeAmount = document.getElementById('changeAmount');
    const customerSelect = document.getElementById('customerSelect');
    const cartCount = document.getElementById('cartCount');
    const categoryFilters = document.getElementById('categoryFilters');
    const heldSalesList = document.getElementById('heldSalesList');
    const deferredCheckbox = document.getElementById('deferredPayment');
    const deferredPaymentRow = document.getElementById('deferredPaymentRow');

    // ── Debounced Search ─────────────────────────────────────────────────
    let searchTimeout;
    let allMedicineCards = [];

    function cacheMedicineCards() {
        allMedicineCards = Array.from(productGrid.querySelectorAll('.medicine-card'));
    }

    function filterBySearch(term) {
        const q = term.toLowerCase().trim();
        productGrid.querySelectorAll('.medicine-card').forEach(card => {
            const name = (card.dataset.name || '').toLowerCase();
            const brand = (card.dataset.brand || '').toLowerCase();
            const barcode = (card.dataset.barcode || '').toLowerCase();
            const generic = (card.dataset.generic || '').toLowerCase();
            const match = !q || name.includes(q) || brand.includes(q) || barcode.includes(q) || generic.includes(q);
            card.style.display = match ? '' : 'none';
        });
    }

    function filterByCategory(categoryId) {
        productGrid.querySelectorAll('.medicine-card').forEach(card => {
            const cat = card.dataset.category || '';
            if (!categoryId || categoryId === 'all' || cat === categoryId) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        // Re-apply search after category change
        if (searchInput && searchInput.value) {
            filterBySearch(searchInput.value);
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            const term = this.value;
            searchTimeout = setTimeout(() => {
                filterBySearch(term);
            }, 80);
        });
    }

    // ── Barcode Scanner Support ──────────────────────────────────────────
    if (barcodeInput) {
        let barcodeBuffer = '';
        let barcodeTimer = null;

        barcodeInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const code = this.value.trim();
                if (code) {
                    addByBarcode(code);
                    this.value = '';
                }
            }
        });

        // Focus barcode input on any keypress when not in a text field
        document.addEventListener('keypress', function (e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                return;
            }
            barcodeInput.focus();
            barcodeInput.value = e.key;
            e.preventDefault();
        });
    }

    async function addByBarcode(barcode) {
        // Find medicine by barcode from the DOM cards first
        const card = productGrid.querySelector(`.medicine-card[data-barcode="${barcode}"]`);
        if (card) {
            const medId = parseInt(card.dataset.id);
            await addToCart(medId, 1);
            return;
        }

        // Fallback: search via API
        try {
            const data = await fetchJSON(`/sales/pos/medicine-search/?q=${encodeURIComponent(barcode)}`);
            if (data.success && data.medicines.length === 1) {
                await addToCart(data.medicines[0].id, 1);
            } else if (data.success && data.medicines.length > 1) {
                // Multiple matches — find exact barcode match
                const exact = data.medicines.find(m => m.barcode === barcode);
                if (exact) {
                    await addToCart(exact.id, 1);
                }
            }
        } catch (err) {
            console.error('Barcode search failed:', err);
        }
    }

    // ── Cart Operations ──────────────────────────────────────────────────

    async function addToCart(medicineId, quantity) {
        try {
            const data = await fetchJSON('/sales/pos/cart/add/', {
                method: 'POST',
                body: JSON.stringify({ medicine_id: medicineId, quantity: quantity || 1 }),
            });
            if (data.success) {
                renderCart(data.cart);
                showToast('Added to cart', 'success');
            }
        } catch (err) {
            console.error('Add to cart failed:', err);
            showToast('Failed to add item', 'danger');
        }
    }

    async function removeFromCart(medicineId) {
        try {
            const data = await fetchJSON('/sales/pos/cart/remove/', {
                method: 'POST',
                body: JSON.stringify({ medicine_id: medicineId }),
            });
            if (data.success) {
                renderCart(data.cart);
                showToast(data.message || 'Item removed', 'info');
            }
        } catch (err) {
            console.error('Remove from cart failed:', err);
        }
    }

    async function updateCartQuantity(medicineId, quantity) {
        try {
            const data = await fetchJSON('/sales/pos/cart/update/', {
                method: 'POST',
                body: JSON.stringify({ medicine_id: medicineId, quantity: quantity }),
            });
            if (data.success) {
                renderCart(data.cart);
            }
        } catch (err) {
            console.error('Update quantity failed:', err);
        }
    }

    async function updateItemDiscount(medicineId, discount) {
        try {
            const data = await fetchJSON('/sales/pos/cart/update/', {
                method: 'POST',
                body: JSON.stringify({ medicine_id: medicineId, discount: discount }),
            });
            if (data.success) {
                renderCart(data.cart);
            }
        } catch (err) {
            console.error('Update item discount failed:', err);
        }
    }

    async function updateDiscount() {
        const type = discountType ? discountType.value : 'flat';
        const value = discountValue ? parseFloat(discountValue.value) || 0 : 0;
        try {
            const data = await fetchJSON('/sales/pos/cart/discount/', {
                method: 'POST',
                body: JSON.stringify({ discount_type: type, discount_value: value }),
            });
            if (data.success) {
                if (cartSubtotal) cartSubtotal.textContent = '৳ ' + parseFloat(data.subtotal).toLocaleString('en-BD', { minimumFractionDigits: 2 });
                if (cartDiscount) cartDiscount.textContent = '৳ ' + parseFloat(data.discount_amount).toLocaleString('en-BD', { minimumFractionDigits: 2 });
                if (cartTax) cartTax.textContent = '৳ ' + parseFloat(data.tax).toLocaleString('en-BD', { minimumFractionDigits: 2 });
                if (cartGrandTotal) cartGrandTotal.textContent = '৳ ' + parseFloat(data.grand_total).toLocaleString('en-BD', { minimumFractionDigits: 2 });
                updateChange();
            }
        } catch (err) {
            console.error('Update discount failed:', err);
        }
    }

    async function refreshCart() {
        try {
            const data = await fetchJSON('/sales/pos/cart/');
            if (data.success) {
                renderCart(data.cart);
            }
        } catch (err) {
            console.error('Refresh cart failed:', err);
        }
    }

    // ── Render Cart ──────────────────────────────────────────────────────

    function renderCart(cartData) {
        if (!cartTableBody) return;

        const items = cartData.items || [];
        cartTableBody.innerHTML = '';

        if (items.length === 0) {
            cartTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <i class="bi bi-cart-x fs-3 d-block mb-2"></i>
                        Cart is empty
                    </td>
                </tr>`;
        } else {
            items.forEach(item => {
                const price = parseFloat(item.price);
                const discount = parseFloat(item.discount || 0);
                const lineBeforeTax = price * item.quantity - discount;
                const taxRate = parseFloat(item.tax_rate || 15);
                const tax = lineBeforeTax * taxRate / 100;
                const lineTotal = lineBeforeTax + tax;

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="col-medicine text-truncate" title="${item.name}">${item.name}</td>
                    <td class="col-qty text-end">
                        <input type="number"
                               class="form-control form-control-sm qty-input"
                               value="${item.quantity}"
                               min="1"
                               step="1"
                               style="width:100%; min-width:40px; display:inline-block; text-align:right;"
                               title="Edit quantity"
                               data-id="${item.id}">
                    </td>
                    <td class="col-price text-end">৳ ${price.toFixed(2)}</td>
                    <td class="col-disc text-end">
                        <input type="number"
                               class="form-control form-control-sm disc-input"
                               value="${discount.toFixed(2)}"
                               min="0"
                               step="0.01"
                               style="width:100%; min-width:55px; display:inline-block; text-align:right;"
                               title="Edit item discount"
                               data-id="${item.id}">
                    </td>
                    <td class="col-total text-end">৳ ${lineTotal.toLocaleString('en-BD', { minimumFractionDigits: 2 })}</td>
                    <td class="col-action text-center">
                        <div class="d-flex gap-1 justify-content-center flex-nowrap">
                            <button class="btn btn-sm btn-outline-secondary qty-dec" data-id="${item.id}" title="Decrease">
                                <i class="bi bi-dash"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-secondary qty-inc" data-id="${item.id}" title="Increase">
                                <i class="bi bi-plus"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger item-remove" data-id="${item.id}" title="Remove">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                cartTableBody.appendChild(row);
            });

            // Bind events
            cartTableBody.querySelectorAll('.qty-dec').forEach(btn => {
                btn.addEventListener('click', function () {
                    const id = parseInt(this.dataset.id);
                    const item = items.find(i => i.id === id);
                    if (item && item.quantity > 1) {
                        updateCartQuantity(id, item.quantity - 1);
                    } else {
                        removeFromCart(id);
                    }
                });
            });

            cartTableBody.querySelectorAll('.qty-inc').forEach(btn => {
                btn.addEventListener('click', function () {
                    const id = parseInt(this.dataset.id);
                    const item = items.find(i => i.id === id);
                    const newQty = (item ? item.quantity : 0) + 1;
                    updateCartQuantity(id, newQty);
                    // Update the input value optimistically
                    const input = cartTableBody.querySelector(`.qty-input[data-id="${id}"]`);
                    if (input) input.value = newQty;
                });
            });

            cartTableBody.querySelectorAll('.item-remove').forEach(btn => {
                btn.addEventListener('click', function () {
                    removeFromCart(parseInt(this.dataset.id));
                });
            });

            // Editable quantity inputs — update cart on change (debounced)
            cartTableBody.querySelectorAll('.qty-input').forEach(input => {
                let inputTimer;
                input.addEventListener('input', function () {
                    const id = parseInt(this.dataset.id);
                    const newQty = parseInt(this.value) || 1;
                    // Clamp to minimum 1
                    if (newQty < 1) this.value = 1;
                    clearTimeout(inputTimer);
                    const self = this;
                    inputTimer = setTimeout(() => {
                        const qty = parseInt(self.value) || 1;
                        updateCartQuantity(id, Math.max(qty, 1));
                    }, 400);
                });
                // Also handle Enter key for immediate update
                input.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        clearTimeout(inputTimer);
                        const id = parseInt(this.dataset.id);
                        const qty = Math.max(parseInt(this.value) || 1, 1);
                        this.value = qty;
                        updateCartQuantity(id, qty);
                    }
                });
                // On blur, ensure the value is valid and update
                input.addEventListener('blur', function () {
                    clearTimeout(inputTimer);
                    const id = parseInt(this.dataset.id);
                    const qty = Math.max(parseInt(this.value) || 1, 1);
                    this.value = qty;
                    updateCartQuantity(id, qty);
                });
            });

            // Editable discount inputs — update cart on change (debounced)
            cartTableBody.querySelectorAll('.disc-input').forEach(input => {
                let discTimer;
                input.addEventListener('input', function () {
                    const id = parseInt(this.dataset.id);
                    const newDisc = parseFloat(this.value);
                    if (isNaN(newDisc) || newDisc < 0) this.value = '0.00';
                    clearTimeout(discTimer);
                    const self = this;
                    discTimer = setTimeout(() => {
                        const disc = Math.max(parseFloat(self.value) || 0, 0);
                        self.value = disc.toFixed(2);
                        updateItemDiscount(id, disc);
                    }, 500);
                });
                input.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        clearTimeout(discTimer);
                        const id = parseInt(this.dataset.id);
                        const disc = Math.max(parseFloat(this.value) || 0, 0);
                        this.value = disc.toFixed(2);
                        updateItemDiscount(id, disc);
                    }
                });
                input.addEventListener('blur', function () {
                    clearTimeout(discTimer);
                    const id = parseInt(this.dataset.id);
                    const disc = Math.max(parseFloat(this.value) || 0, 0);
                    this.value = disc.toFixed(2);
                    updateItemDiscount(id, disc);
                });
            });
        }

        // Update summary
        if (cartSubtotal) cartSubtotal.textContent = '৳ ' + parseFloat(cartData.subtotal || 0).toLocaleString('en-BD', { minimumFractionDigits: 2 });
        if (cartDiscount) cartDiscount.textContent = '৳ ' + parseFloat(cartData.discount || 0).toLocaleString('en-BD', { minimumFractionDigits: 2 });
        if (cartTax) cartTax.textContent = '৳ ' + parseFloat(cartData.tax || 0).toLocaleString('en-BD', { minimumFractionDigits: 2 });
        if (cartGrandTotal) cartGrandTotal.textContent = '৳ ' + parseFloat(cartData.grand_total || 0).toLocaleString('en-BD', { minimumFractionDigits: 2 });
        if (cartCount) cartCount.textContent = cartData.count || 0;

        // Auto-fill amount paid to grand total for convenience
        const gt = parseFloat(cartData.grand_total || 0);
        if (amountPaid) {
            amountPaid.value = gt.toFixed(2);
        }

        updateChange();
    }

    // ── Payment Change Calculation ───────────────────────────────────────

    function updateChange() {
        if (!amountPaid || !changeAmount || !cartGrandTotal) return;

        const paid = parseFloat(amountPaid.value) || 0;
        const totalText = cartGrandTotal.textContent.replace(/[^0-9.\-]/g, '');
        const total = parseFloat(totalText) || 0;
        const change = Math.max(paid - total, 0);

        changeAmount.textContent = '৳ ' + change.toLocaleString('en-BD', { minimumFractionDigits: 2 });

        if (paid > 0 && paid < total) {
            changeAmount.classList.add('text-danger');
        } else {
            changeAmount.classList.remove('text-danger');
        }
    }

    if (amountPaid) {
        amountPaid.addEventListener('input', updateChange);
    }

    // ── Discount Change Handlers ─────────────────────────────────────────

    if (discountType) {
        discountType.addEventListener('change', updateDiscount);
    }
    if (discountValue) {
        discountValue.addEventListener('input', function () {
            clearTimeout(this._discountTimer);
            this._discountTimer = setTimeout(updateDiscount, 300);
        });
    }

    // ── Customer Selection ───────────────────────────────────────────────

    if (customerSelect) {
        customerSelect.addEventListener('change', async function () {
            const customerId = this.value || null;

            // Show/hide deferred payment when a customer is selected/deselected
            if (customerId && deferredPaymentRow) {
                deferredPaymentRow.style.display = '';
            } else {
                if (deferredPaymentRow) deferredPaymentRow.style.display = 'none';
                if (deferredCheckbox) deferredCheckbox.checked = false;
            }

            try {
                const data = await fetchJSON('/sales/pos/cart/customer/', {
                    method: 'POST',
                    body: JSON.stringify({ customer_id: customerId }),
                });
                if (data.success) {
                    showToast(customerId ? 'Customer selected' : 'Customer cleared', 'info');
                }
            } catch (err) {
                console.error('Set customer failed:', err);
            }
        });
    }

    // ── Product Grid Click Handler ───────────────────────────────────────

    if (productGrid) {
        productGrid.addEventListener('click', function (e) {
            const card = e.target.closest('.medicine-card, .medicine-list-item');
            if (!card) return;

            const medId = parseInt(card.dataset.id);
            if (medId) {
                addToCart(medId, 1);
            }
        });
    }

    // ── Category Filter Pills ────────────────────────────────────────────

    if (categoryFilters) {
        categoryFilters.addEventListener('click', function (e) {
            const pill = e.target.closest('.category-pill');
            if (!pill) return;

            // Update active state
            categoryFilters.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const categoryId = pill.dataset.category || 'all';
            filterByCategory(categoryId);
        });
    }

    // ── Checkout ─────────────────────────────────────────────────────────

    const checkoutBtn = document.getElementById('checkoutBtn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            const items = cartTableBody ? cartTableBody.querySelectorAll('tr:not(:has(td[colspan]))') : [];
            if (items.length === 0) {
                showToast('Cart is empty!', 'warning');
                return;
            }

            const paid = amountPaid ? parseFloat(amountPaid.value) || 0 : 0;
            const totalText = cartGrandTotal ? cartGrandTotal.textContent.replace(/[^0-9.\-]/g, '') : '0';
            const total = parseFloat(totalText) || 0;

            const deferred = deferredCheckbox ? deferredCheckbox.checked : false;

            if (!deferred && paid < total) {
                showToast('Insufficient payment amount!', 'danger');
                return;
            }

            if (deferred && paid >= total) {
                showToast('Payment covers full amount - deferred not needed.', 'warning');
                return;
            }

            const mode = paymentMode ? paymentMode.value : 'CASH';

            // Submit via form POST for proper redirect
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/sales/pos/checkout/';

            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = CSRF_TOKEN;
            form.appendChild(csrfInput);

            const bodyInput = document.createElement('input');
            bodyInput.type = 'hidden';
            bodyInput.name = 'body';
            bodyInput.value = JSON.stringify({
                payment_mode: mode,
                amount_paid: paid,
                deferred: deferred,
                notes: '',
            });
            form.appendChild(bodyInput);

            document.body.appendChild(form);
            form.submit();
        });
    }

    // ── Hold Sale ────────────────────────────────────────────────────────

    const holdBtn = document.getElementById('holdBtn');
    if (holdBtn) {
        holdBtn.addEventListener('click', function () {
            const items = cartTableBody ? cartTableBody.querySelectorAll('tr:not(:has(td[colspan]))') : [];
            if (items.length === 0) {
                showToast('Cart is empty!', 'warning');
                return;
            }

            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/sales/pos/hold/';

            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = CSRF_TOKEN;
            form.appendChild(csrfInput);

            document.body.appendChild(form);
            form.submit();
        });
    }

    // ── Clear Cart ───────────────────────────────────────────────────────

    const clearBtn = document.getElementById('clearCartBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async function () {
            const items = cartTableBody ? cartTableBody.querySelectorAll('tr:not(:has(td[colspan]))') : [];
            if (items.length === 0) return;

            if (!confirm('Clear all items from the cart?')) return;

            // Remove each item
            for (const row of items) {
                const removeBtn = row.querySelector('.item-remove');
                if (removeBtn) {
                    const id = parseInt(removeBtn.dataset.id);
                    await removeFromCart(id);
                }
            }
            refreshCart();
            showToast('Cart cleared', 'info');
        });
    }

    // ── Resume Held Sale ─────────────────────────────────────────────────

    if (heldSalesList) {
        heldSalesList.addEventListener('click', function (e) {
            const resumeBtn = e.target.closest('.resume-sale');
            if (!resumeBtn) return;

            const saleId = resumeBtn.dataset.saleId;
            if (saleId) {
                window.location.href = `/sales/pos/resume/${saleId}/`;
            }
        });
    }

    // ── Toast Notification ───────────────────────────────────────────────

    function showToast(message, type) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>`;
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: 2000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    // ── Grid / List View Toggle ────────────────────────────────────────

    const viewGridBtn = document.getElementById('viewGridBtn');
    const viewListBtn = document.getElementById('viewListBtn');
    let currentView = 'list';  // 'grid' or 'list'

    function setViewMode(mode) {
        currentView = mode;

        if (viewGridBtn && viewListBtn) {
            viewGridBtn.classList.toggle('active', mode === 'grid');
            viewListBtn.classList.toggle('active', mode === 'list');
        }

        if (mode === 'list') {
            convertToListView();
        } else {
            convertToGridView();
        }
    }

    function convertToListView() {
        const cards = Array.from(productGrid.querySelectorAll('.medicine-card'));
        if (cards.length === 0) return;

        // Replace grid classes with list container
        productGrid.classList.remove('row', 'row-cols-2', 'row-cols-md-3', 'g-2');
        productGrid.classList.add('list-container');
        productGrid.innerHTML = '';

        cards.forEach(card => {
            const parentCol = card.parentElement;
            const icon = card.dataset.unitIcon || 'bi-capsule';
            const name = card.dataset.name || '';
            const brand = card.dataset.brand || '';
            const price = card.dataset.price || '0';
            const unit = card.dataset.unit || 'Pcs';
            const stockBadge = card.querySelector('.med-stock');
            const stockText = stockBadge ? stockBadge.textContent.trim() : '0 Pcs';

            const listItem = document.createElement('div');
            listItem.className = 'medicine-list-item';
            listItem.setAttribute('data-id', card.dataset.id || '');
            listItem.setAttribute('data-name', card.dataset.name || '');
            listItem.setAttribute('data-brand', card.dataset.brand || '');
            listItem.setAttribute('data-barcode', card.dataset.barcode || '');
            listItem.setAttribute('data-generic', card.dataset.generic || '');
            listItem.setAttribute('data-category', card.dataset.category || '');
            listItem.setAttribute('data-price', card.dataset.price || '');
            listItem.setAttribute('data-unit-icon', icon);
            listItem.setAttribute('data-unit', unit);

            listItem.innerHTML = `
                <span class="med-icon"><i class="bi ${icon}"></i></span>
                <span class="med-name" title="${name}">${name}</span>
                ${brand ? `<span class="med-brand" title="${brand}">${brand}</span>` : ''}
                <span class="med-price">৳ ${parseFloat(price).toLocaleString('en-BD', {minimumFractionDigits: 2})}</span>
                <span class="med-stock">${stockText}</span>
            `;
            productGrid.appendChild(listItem);
        });

        // Re-apply current search filter
        if (searchInput && searchInput.value) {
            filterBySearch(searchInput.value);
        }
    }

    function convertToGridView() {
        const listItems = Array.from(productGrid.querySelectorAll('.medicine-list-item'));
        if (listItems.length === 0) return;

        productGrid.classList.remove('list-container');
        productGrid.classList.add('row', 'row-cols-2', 'row-cols-md-3', 'g-2');
        productGrid.innerHTML = '';

        listItems.forEach(item => {
            const icon = item.dataset.unitIcon || 'bi-capsule';
            const name = item.dataset.name || '';
            const brand = item.dataset.brand || '';
            const price = item.dataset.price || '0';
            const unit = item.dataset.unit || 'Pcs';
            const stockEl = item.querySelector('.med-stock');
            const stockText = stockEl ? stockEl.textContent.trim() : '0 Pcs';
            const stockNum = parseInt(stockText) || 0;
            const stockClass = stockNum > 10 ? 'bg-success' : (stockNum > 0 ? 'bg-warning text-dark' : 'bg-danger');

            const col = document.createElement('div');
            col.className = 'col';

            const card = document.createElement('div');
            card.className = 'medicine-card';
            card.setAttribute('data-id', item.dataset.id || '');
            card.setAttribute('data-name', item.dataset.name || '');
            card.setAttribute('data-brand', item.dataset.brand || '');
            card.setAttribute('data-barcode', item.dataset.barcode || '');
            card.setAttribute('data-generic', item.dataset.generic || '');
            card.setAttribute('data-category', item.dataset.category || '');
            card.setAttribute('data-price', item.dataset.price || '');
            card.setAttribute('data-unit-icon', icon);
            card.setAttribute('data-unit', unit);

            card.innerHTML = `
                <div class="d-flex align-items-center gap-2 mb-1">
                    <span class="med-icon"><i class="bi ${icon}"></i></span>
                    <div class="med-name">${name}</div>
                </div>
                ${brand ? `<div class="med-brand mb-1">${brand}</div>` : ''}
                <div class="d-flex justify-content-between align-items-center mt-auto">
                    <span class="med-price">৳ ${parseFloat(price).toLocaleString('en-BD', {minimumFractionDigits: 2})}</span>
                    <span class="badge ${stockClass} med-stock">${stockText}</span>
                </div>
            `;
            col.appendChild(card);
            productGrid.appendChild(col);
        });

        // Re-apply current search filter
        if (searchInput && searchInput.value) {
            filterBySearch(searchInput.value);
        }
    }

    if (viewGridBtn) {
        viewGridBtn.addEventListener('click', function () {
            if (currentView !== 'grid') setViewMode('grid');
        });
    }

    if (viewListBtn) {
        viewListBtn.addEventListener('click', function () {
            if (currentView !== 'list') setViewMode('list');
        });
    }

    // Extend filterByCategory and filterBySearch to support list items
    const origFilterBySearch = filterBySearch;
    filterBySearch = function (term) {
        const q = term.toLowerCase().trim();
        const items = productGrid.querySelectorAll('.medicine-card, .medicine-list-item');
        items.forEach(item => {
            const name = (item.dataset.name || '').toLowerCase();
            const brand = (item.dataset.brand || '').toLowerCase();
            const barcode = (item.dataset.barcode || '').toLowerCase();
            const generic = (item.dataset.generic || '').toLowerCase();
            const match = !q || name.includes(q) || brand.includes(q) || barcode.includes(q) || generic.includes(q);
            item.style.display = match ? '' : 'none';
            // Also hide parent col for grid view
            if (item.classList.contains('medicine-card')) {
                const parentCol = item.closest('.col');
                if (parentCol) parentCol.style.display = match ? '' : 'none';
            }
        });
    };

    const origFilterByCategory = filterByCategory;
    filterByCategory = function (categoryId) {
        const items = productGrid.querySelectorAll('.medicine-card, .medicine-list-item');
        items.forEach(item => {
            const cat = item.dataset.category || '';
            if (!categoryId || categoryId === 'all' || cat === categoryId) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
            if (item.classList.contains('medicine-card')) {
                const parentCol = item.closest('.col');
                if (parentCol) {
                    parentCol.style.display = (!categoryId || categoryId === 'all' || cat === categoryId) ? '' : 'none';
                }
            }
        });
        if (searchInput && searchInput.value) {
            filterBySearch(searchInput.value);
        }
    };

    // ── Initial Load ─────────────────────────────────────────────────────

    // ── Draggable Panel Divider ────────────────────────────────────────

    const posRow = document.getElementById('posRow');
    const posLeft = document.getElementById('posLeft');
    const posDivider = document.getElementById('posDivider');
    const posRight = document.getElementById('posRight');

    let isDragging = false;
    let startX = 0;
    let startLeftWidth = 0;

    if (posDivider && posLeft && posRight && posRow) {
        posDivider.addEventListener('mousedown', function (e) {
            isDragging = true;
            startX = e.clientX;
            startLeftWidth = posLeft.offsetWidth;
            posDivider.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!isDragging) return;
            const deltaX = e.clientX - startX;
            const newLeftWidth = startLeftWidth + deltaX;
            const containerWidth = posRow.offsetWidth - posDivider.offsetWidth;
            // Clamp: min 280px, max 80% of container
            const clampedWidth = Math.max(280, Math.min(newLeftWidth, containerWidth * 0.8));
            posLeft.style.flex = '0 0 ' + clampedWidth + 'px';
        });

        document.addEventListener('mouseup', function () {
            if (!isDragging) return;
            isDragging = false;
            posDivider.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        });

        // Touch support
        posDivider.addEventListener('touchstart', function (e) {
            isDragging = true;
            startX = e.touches[0].clientX;
            startLeftWidth = posLeft.offsetWidth;
            posDivider.classList.add('active');
            document.body.style.userSelect = 'none';
            e.preventDefault();
        }, { passive: false });

        document.addEventListener('touchmove', function (e) {
            if (!isDragging) return;
            const deltaX = e.touches[0].clientX - startX;
            const newLeftWidth = startLeftWidth + deltaX;
            const containerWidth = posRow.offsetWidth - posDivider.offsetWidth;
            const clampedWidth = Math.max(280, Math.min(newLeftWidth, containerWidth * 0.8));
            posLeft.style.flex = '0 0 ' + clampedWidth + 'px';
        }, { passive: false });

        document.addEventListener('touchend', function () {
            if (!isDragging) return;
            isDragging = false;
            posDivider.classList.remove('active');
            document.body.style.userSelect = '';
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        cacheMedicineCards();
        refreshCart();
        // Activate list view by default
        setViewMode('list');
    });

})();