/* ==========================================================
   HISOBCHI AI — EXACT REPRODUCTION OF USER DESKTOP & MOBILE UI
   Seamless live sync with Telegram Bot & SQLite database
   Clean, simple, no emojis, distinct Income & Expense categories.
   ========================================================== */

const EXPENSE_CATEGORIES = [
    "Oziq-ovqat",
    "Transport",
    "Xaridlar",
    "Kommunal",
    "Sog'liq",
    "Boshqa"
];

const INCOME_CATEGORIES = [
    "Maosh",
    "Bonus",
    "Sovg'a",
    "Boshqa"
];

const state = {
    userId: 5111794979, // Default fallback (Parviz)
    userName: "Parviz",
    period: "month",
    activeTab: "analytics",
    summary: null,
    transactions: [],
    debts: { given: [], taken: [], total_given: 0, total_taken: 0 },
    budgets: [],
    selectedTxType: "expense",
    selectedMethod: "Naqd",
    selectedCategory: "Oziq-ovqat",
    selectedDebtType: "given",
    isRecordingVoice: false
};

// Prototype Palette
const PALETTE = [
    "#0F2A5C",
    "#3B6FD4",
    "#8FB0EA",
    "#CBD8F0",
    "#94A3B8",
    "#64748B",
    "#047857",
    "#D97706"
];

const DOM = {
    userAvatar: document.getElementById("userAvatar"),
    userSelector: document.getElementById("userSelector"),
    userNameTitle: document.getElementById("userNameTitle"),
    netBalance: document.getElementById("netBalance"),
    cashBalance: document.getElementById("cashBalance"),
    cardBalance: document.getElementById("cardBalance"),
    totalIncome: document.getElementById("totalIncome"),
    totalExpense: document.getElementById("totalExpense"),
    periodSegments: document.getElementById("periodSegments"),
    mainTabStrip: document.getElementById("mainTabStrip"),
    catCountSubtitle: document.getElementById("catCountSubtitle"),
    multiProgressBar: document.getElementById("multiProgressBar"),
    categoryChipsGrid: document.getElementById("categoryChipsGrid"),
    recentTxList: document.getElementById("recentTxList"),
    transactionsList: document.getElementById("transactionsList"),
    txSearchInput: document.getElementById("txSearchInput"),
    debtTotalGiven: document.getElementById("debtTotalGiven"),
    debtTotalTaken: document.getElementById("debtTotalTaken"),
    debtsList: document.getElementById("debtsList"),
    budgetsList: document.getElementById("budgetsList"),
    overallBudgetAmount: document.getElementById("overallBudgetAmount"),
    overallBudgetFill: document.getElementById("overallBudgetFill"),
    overallBudgetRemaining: document.getElementById("overallBudgetRemaining"),
    toastContainer: document.getElementById("toastContainer")
};

// ==================== HELPER: EMOJI REMOVER ====================
function cleanText(str) {
    if (!str) return "";
    return str.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}]/gu, '').trim();
}

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", async () => {
    initTelegramWebApp();
    await initUsers();
    setupEventListeners();
    refreshAll();
});

function initTelegramWebApp() {
    if (window.Telegram && window.Telegram.WebApp) {
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();

        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            const u = tg.initDataUnsafe.user;
            state.userId = u.id;
            state.userName = u.first_name || u.username || "Parviz";
        }
    }

    const urlParams = new URLSearchParams(window.location.search);
    const qUserId = urlParams.get("user_id");
    if (qUserId) {
        state.userId = parseInt(qUserId, 10);
    }
}

async function initUsers() {
    try {
        const res = await fetch("/api/users");
        if (res.ok) {
            const users = await res.json();
            DOM.userSelector.innerHTML = "";
            let found = false;

            users.forEach(u => {
                const opt = document.createElement("option");
                opt.value = u.user_id;
                opt.textContent = `${cleanText(u.full_name) || 'Parviz'}`;
                if (u.user_id === state.userId) {
                    opt.selected = true;
                    found = true;
                    state.userName = u.full_name || "Parviz";
                }
                DOM.userSelector.appendChild(opt);
            });

            if (!found && users.length > 0) {
                state.userId = users[0].user_id;
                state.userName = users[0].full_name || "Parviz";
                DOM.userSelector.value = state.userId;
            }
        }
    } catch (e) {
        console.error("Users load error:", e);
    }

    updateUserUI();
}

function updateUserUI() {
    const cleanName = cleanText(state.userName) || "Parviz";
    DOM.userAvatar.textContent = cleanName.charAt(0).toUpperCase();
    if (DOM.userNameTitle) DOM.userNameTitle.textContent = cleanName;
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    // User Switcher
    DOM.userSelector.addEventListener("change", (e) => {
        state.userId = parseInt(e.target.value, 10);
        state.userName = e.target.options[e.target.selectedIndex].text;
        updateUserUI();
        refreshAll();
    });

    // Period Segmented Control
    const segButtons = DOM.periodSegments.querySelectorAll(".period-btn");
    segButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            segButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.period = btn.dataset.period;
            refreshDashboard();
            loadTransactions();
        });
    });

    // Nav Tabs (Sidebar Buttons: Tahlil, Tarix, Qarzlar, Byudjet)
    const tabButtons = DOM.mainTabStrip.querySelectorAll(".sidebar-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            switchTab(btn.dataset.tab);
        });
    });

    // View All button on Tahlil panel
    document.getElementById("btnViewAllHistory")?.addEventListener("click", () => {
        switchTab("history");
    });

    // Modals open / close
    setupModalHandlers();

    // Excel Export
    document.getElementById("exportExcelBtn").addEventListener("click", () => {
        showToast("Excel fayli tayyorlanmoqda...");
        window.location.href = `/api/excel/download?user_id=${state.userId}&period=${state.period}`;
    });

    // AI Chat Screen
    document.getElementById("aiAdviceBtn").addEventListener("click", () => {
        openAIChat();
        // Auto-send summary on first open
        if (document.getElementById("aiChatMessages").children.length === 0) {
            sendAIChatQuery("summary", "Shu oy xulosasi");
        }
    });

    document.getElementById("aiChatBackBtn").addEventListener("click", closeAIChat);

    // AI Chat Send
    document.getElementById("aiChatSendBtn").addEventListener("click", () => {
        const input = document.getElementById("aiChatInput");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        sendAIChatQuery("custom", text);
    });

    document.getElementById("aiChatInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            document.getElementById("aiChatSendBtn").click();
        }
    });

    // AI Quick Chips
    document.querySelectorAll(".ai-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            sendAIChatQuery(chip.dataset.query, chip.textContent);
        });
    });

    // Add Transaction
    document.getElementById("fabAddTransaction").addEventListener("click", () => {
        openModal("modalAddTransaction");
    });

    // Form Handlers
    setupAddTransactionForm();
    setupReceiptScanner();
    setupSmartInput();
    setupDebtAndBudgetForms();

    // Search in Transactions
    DOM.txSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        renderTransactions(query);
    });
}

function switchTab(targetTab) {
    state.activeTab = targetTab;
    const tabButtons = DOM.mainTabStrip.querySelectorAll(".sidebar-btn");
    tabButtons.forEach(b => {
        b.classList.toggle("active", b.dataset.tab === targetTab);
    });

    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    const activePanel = document.getElementById(`tab-${targetTab}`);
    if (activePanel) activePanel.classList.add("active");

    if (targetTab === "history") loadTransactions();
    else if (targetTab === "debts") loadDebts();
    else if (targetTab === "budgets") loadBudgets();
}

// ==================== DASHBOARD REFRESH ====================
async function refreshAll() {
    await refreshDashboard();
    await loadDebts();
    await loadBudgets();
}

async function refreshDashboard() {
    try {
        const res = await fetch(`/api/summary?user_id=${state.userId}&period=${state.period}`);
        if (!res.ok) throw new Error("Summary fetch failed");
        const data = await res.json();
        state.summary = data;

        const sign = data.balance < 0 ? "−" : "";
        DOM.netBalance.innerHTML = `${sign}${formatNumber(Math.abs(data.balance))} <span class="balance-curr">so'm</span>`;
        DOM.totalIncome.textContent = `+${formatNumber(data.income)}`;
        DOM.totalExpense.textContent = `−${formatNumber(data.expense)}`;

        const cashSign = data.cash_balance < 0 ? "−" : "";
        const cardSign = data.card_balance < 0 ? "−" : "";
        DOM.cashBalance.textContent = `${cashSign}${formatNumber(Math.abs(data.cash_balance))}`;
        DOM.cardBalance.textContent = `${cardSign}${formatNumber(Math.abs(data.card_balance))}`;

        renderDistribution(data.categories, data.expense);
        renderRecentTransactions(data.recent);
    } catch (e) {
        console.error("Dashboard refresh error:", e);
    }
}

// ==================== MULTI-PROGRESS BAR & CHIPS ====================
function renderDistribution(categories, totalExpense) {
    DOM.multiProgressBar.innerHTML = "";
    DOM.categoryChipsGrid.innerHTML = "";
    DOM.catCountSubtitle.textContent = `${categories ? categories.length : 0} toifa`;

    if (!categories || categories.length === 0 || totalExpense <= 0) {
        DOM.multiProgressBar.innerHTML = `<div class="progress-seg" style="flex:100;background:#CBD8F0"></div>`;
        DOM.categoryChipsGrid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 16px 0; font-size: 13px;">
                Hozircha xarajatlar mavjud emas
            </div>
        `;
        return;
    }

    categories.forEach((cat, idx) => {
        const color = PALETTE[idx % PALETTE.length];
        const weight = Math.max(2, Math.round((cat.sum_amount / totalExpense) * 100));
        const catName = cleanText(cat.category);

        // Segment bar
        const seg = document.createElement("div");
        seg.className = "progress-seg";
        seg.style.flex = weight.toString();
        seg.style.background = color;
        DOM.multiProgressBar.appendChild(seg);

        // Chip item
        const chip = document.createElement("div");
        chip.className = "cat-item-row";
        chip.innerHTML = `
            <div class="cat-dot-name">
                <span class="cat-dot" style="background: ${color};"></span>
                <span>${catName}</span>
            </div>
            <div style="font-weight: 600; font-size: 13px; color: var(--text-main);">
                ${formatNumber(cat.sum_amount)}
            </div>
        `;
        DOM.categoryChipsGrid.appendChild(chip);
    });
}

function renderRecentTransactions(recent) {
    if (!DOM.recentTxList) return;
    DOM.recentTxList.innerHTML = "";

    if (!recent || recent.length === 0) {
        DOM.recentTxList.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 20px 0; font-size: 13px;">
                Amallar yo'q
            </div>
        `;
        return;
    }

    recent.slice(0, 4).forEach(t => {
        const isExp = t.type === "expense";
        const sign = isExp ? "−" : "+";
        const amtColor = isExp ? "var(--expense-color)" : "var(--income-color)";
        const catName = cleanText(t.category);
        const initial = catName.charAt(0).toUpperCase() || "O";
        const payMethod = cleanText(t.payment_method) || "Naqd";

        const item = document.createElement("div");
        item.className = "tx-item";
        item.innerHTML = `
            <div class="tx-icon-pill">${initial}</div>
            <div class="tx-details">
                <div class="tx-title">${catName}</div>
                <div class="tx-meta">${formatDate(t.created_at)}, ${payMethod.toLowerCase()}</div>
            </div>
            <div class="tx-amount" style="color: ${amtColor};">${sign}${formatNumber(t.amount)}</div>
        `;
        DOM.recentTxList.appendChild(item);
    });
}

// ==================== TRANSACTIONS (TARIX TAB) ====================
async function loadTransactions() {
    try {
        const res = await fetch(`/api/transactions?user_id=${state.userId}&period=${state.period}`);
        if (!res.ok) throw new Error("Transactions fetch failed");
        state.transactions = await res.json();
        renderTransactions();
    } catch (e) {
        console.error("Load transactions error:", e);
    }
}

function renderTransactions(filterQuery = "") {
    DOM.transactionsList.innerHTML = "";
    let items = state.transactions;

    if (filterQuery) {
        items = items.filter(t => 
            (t.description && t.description.toLowerCase().includes(filterQuery)) ||
            (t.category && t.category.toLowerCase().includes(filterQuery))
        );
    }

    if (!items || items.length === 0) {
        DOM.transactionsList.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 32px 0; font-size: 14px;">
                Hozircha amallar yo'q
            </div>
        `;
        return;
    }

    items.forEach(t => {
        const isExp = t.type === "expense";
        const sign = isExp ? "−" : "+";
        const amtColor = isExp ? "var(--expense-color)" : "var(--income-color)";
        const catName = cleanText(t.category);
        const initial = catName.charAt(0).toUpperCase() || "O";
        const payMethod = cleanText(t.payment_method) || "Naqd";
        const descText = cleanText(t.description) || "Izohsiz";

        const item = document.createElement("div");
        item.className = "tx-item";
        item.innerHTML = `
            <div class="tx-icon-pill">${initial}</div>
            <div class="tx-details">
                <div class="tx-title">${catName} <span style="font-size:12px;color:var(--text-muted);font-weight:400;">(${descText})</span></div>
                <div class="tx-meta">${payMethod} • ${formatDate(t.created_at)}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="tx-amount" style="color: ${amtColor};">${sign}${formatNumber(t.amount)}</span>
                <button class="tx-del-btn" data-id="${t.id}" title="O'chirish">✕</button>
            </div>
        `;

        item.querySelector(".tx-del-btn").addEventListener("click", () => deleteTx(t.id));
        DOM.transactionsList.appendChild(item);
    });
}

async function deleteTx(id) {
    if (!confirm("Ushbu yozuvni o'chirmoqchimisiz?")) return;
    try {
        const res = await fetch(`/api/transactions/${id}?user_id=${state.userId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("O'chirildi");
            await refreshDashboard();
            await loadTransactions();
            await loadBudgets();
        }
    } catch (e) {
        showToast("Xatolik");
    }
}

// ==================== DEBTS (QARZLAR TAB) ====================
async function loadDebts() {
    try {
        const res = await fetch(`/api/debts?user_id=${state.userId}`);
        if (!res.ok) throw new Error("Debts fetch failed");
        const debts = await res.json();
        state.debts = debts;

        DOM.debtTotalGiven.textContent = `${formatNumber(debts.total_given)} so'm`;
        DOM.debtTotalTaken.textContent = `${formatNumber(debts.total_taken)} so'm`;

        DOM.debtsList.innerHTML = "";
        const allDebts = [...debts.given, ...debts.taken];

        if (allDebts.length === 0) {
            DOM.debtsList.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 24px 0; font-size: 13px;">
                    Faol qarzlar yo'q
                </div>
            `;
            return;
        }

        allDebts.forEach(d => {
            const isGiven = d.debt_type === "given";
            const tag = isGiven ? "Menga berishi kerak" : "Men berishim kerak";
            const personName = cleanText(d.person_name);
            const initial = personName.charAt(0).toUpperCase() || "Q";
            const desc = cleanText(d.description) || "Izohsiz";

            const item = document.createElement("div");
            item.className = "tx-item";
            item.innerHTML = `
                <div class="tx-icon-pill">${initial}</div>
                <div class="tx-details">
                    <div class="tx-title">${personName}</div>
                    <div class="tx-meta">${tag} • ${desc}</div>
                </div>
                <div style="text-align: right;">
                    <div class="tx-amount" style="margin-bottom: 6px;">${formatNumber(d.amount)} so'm</div>
                    <button class="btn-secondary" style="height: 32px; padding: 0 14px; font-size: 12px; border-radius: 16px;" data-id="${d.id}">To'landi</button>
                </div>
            `;

            item.querySelector("button").addEventListener("click", () => payDebt(d.id));
            DOM.debtsList.appendChild(item);
        });
    } catch (e) {
        console.error("Load debts error:", e);
    }
}

async function payDebt(id) {
    try {
        const res = await fetch(`/api/debts/${id}/pay?user_id=${state.userId}`, { method: "POST" });
        if (res.ok) {
            showToast("Qarz yopildi");
            loadDebts();
        }
    } catch (e) {
        showToast("Xatolik");
    }
}

// ==================== BUDGETS (BYUDJET TAB) ====================
async function loadBudgets() {
    try {
        const res = await fetch(`/api/budgets?user_id=${state.userId}`);
        if (!res.ok) throw new Error("Budgets fetch failed");
        const budgets = await res.json();
        state.budgets = budgets;

        DOM.budgetsList.innerHTML = "";
        
        let overall = budgets.find(b => cleanText(b.category).toLowerCase() === "umumiy");
        if (overall) {
            const pct = Math.min(overall.percent, 100);
            DOM.overallBudgetAmount.innerHTML = `${formatNumber(overall.spent)} <span style="font-size:14px;font-weight:500;color:var(--text-muted)">/ ${formatNumber(overall.monthly_limit)} so'm</span>`;
            DOM.overallBudgetFill.style.width = `${pct}%`;
            DOM.overallBudgetFill.className = `budget-fill ${overall.percent >= 100 ? 'danger' : (overall.percent >= 80 ? 'warning' : '')}`;
            DOM.overallBudgetRemaining.textContent = `Qoldi: ${formatNumber(overall.remaining)} so'm`;
        } else {
            DOM.overallBudgetAmount.textContent = "Limit belgilanmagan";
            DOM.overallBudgetFill.style.width = "0%";
            DOM.overallBudgetRemaining.textContent = "Sozlash tugmasini bosing";
        }

        const categoryBudgets = budgets.filter(b => cleanText(b.category).toLowerCase() !== "umumiy");

        if (categoryBudgets.length === 0) {
            DOM.budgetsList.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 24px 0; font-size: 13px;">
                    Toifalar bo'yicha limitlar yo'q
                </div>
            `;
            return;
        }

        categoryBudgets.forEach(b => {
            const pct = Math.min(b.percent, 100);
            let fillClass = "";
            if (b.percent >= 100) fillClass = "danger";
            else if (b.percent >= 80) fillClass = "warning";
            const catName = cleanText(b.category);

            const row = document.createElement("div");
            row.style.padding = "14px 0";
            row.style.borderBottom = "1px solid rgba(15,42,92,.08)";
            row.innerHTML = `
                <div style="display:flex;justify-content:space-between;font-size:14px;">
                    <span style="font-weight:500">${catName}</span>
                    <span style="color:var(--text-muted);font-size:12px;">${formatNumber(b.spent)} / ${formatNumber(b.monthly_limit)}</span>
                </div>
                <div class="budget-track" style="margin-top:10px;height:6px;">
                    <div class="budget-fill ${fillClass}" style="width:${pct}%;height:6px;"></div>
                </div>
            `;
            DOM.budgetsList.appendChild(row);
        });
    } catch (e) {
        console.error("Load budgets error:", e);
    }
}

// ==================== DYNAMIC CATEGORY PILLS ====================
function renderCategoryPills() {
    const picker = document.getElementById("categoryPicker");
    const descInput = document.getElementById("txDescription");
    picker.innerHTML = "";

    const categories = state.selectedTxType === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;

    if (!categories.includes(state.selectedCategory)) {
        state.selectedCategory = categories[0];
    }

    categories.forEach(cat => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `pill-btn ${cat === state.selectedCategory ? 'active' : ''}`;
        btn.dataset.cat = cat;
        btn.textContent = cat;
        btn.addEventListener("click", () => {
            picker.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.selectedCategory = cat;
        });
        picker.appendChild(btn);
    });

    if (state.selectedTxType === "income") {
        descInput.placeholder = "Masalan: oylik maosh";
    } else {
        descInput.placeholder = "Masalan: tushlik yoki supermarket";
    }
}

// ==================== FORMS & ACTIONS ====================
function setupAddTransactionForm() {
    const expenseBtn = document.getElementById("btnTypeExpense");
    const incomeBtn = document.getElementById("btnTypeIncome");
    const methodChips = document.querySelectorAll("#methodChips .pill-btn");
    const amountInput = document.getElementById("txAmount");
    const descInput = document.getElementById("txDescription");
    const saveBtn = document.getElementById("btnSaveTransaction");

    renderCategoryPills();

    expenseBtn.addEventListener("click", () => {
        expenseBtn.classList.add("active");
        incomeBtn.classList.remove("active");
        state.selectedTxType = "expense";
        renderCategoryPills();
    });

    incomeBtn.addEventListener("click", () => {
        incomeBtn.classList.add("active");
        expenseBtn.classList.remove("active");
        state.selectedTxType = "income";
        renderCategoryPills();
    });

    methodChips.forEach(chip => {
        chip.addEventListener("click", () => {
            methodChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            state.selectedMethod = cleanText(chip.dataset.method);
        });
    });

    saveBtn.addEventListener("click", async () => {
        const amt = parseFloat(amountInput.value);
        if (!amt || amt <= 0) {
            alert("Iltimos, summani kiriting!");
            return;
        }

        saveBtn.disabled = true;
        saveBtn.textContent = "Saqlanmoqda...";

        try {
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: state.userId,
                    trans_type: state.selectedTxType,
                    amount: amt,
                    category: state.selectedCategory,
                    description: descInput.value.trim(),
                    payment_method: state.selectedMethod
                })
            });

            if (res.ok) {
                const data = await res.json();
                showToast("Saqlandi");
                if (data.alerts && data.alerts.length > 0) {
                    data.alerts.forEach(al => alert(cleanText(al.replace(/<[^>]*>?/gm, ''))));
                }
                amountInput.value = "";
                descInput.value = "";
                closeModal("modalAddTransaction");
                await refreshDashboard();
                await loadTransactions();
                await loadBudgets();
            }
        } catch (e) {
            showToast("Xatolik");
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = "Saqlash";
        }
    });
}

let activeCameraStream = null;
let currentFacingMode = "environment";

function stopCameraStream() {
    if (activeCameraStream) {
        try {
            activeCameraStream.getTracks().forEach(track => track.stop());
        } catch (e) {
            console.error("Error stopping tracks:", e);
        }
        activeCameraStream = null;
    }
    const video = document.getElementById("cameraVideo");
    if (video) video.srcObject = null;
    const viewport = document.getElementById("cameraViewportWrap");
    if (viewport) viewport.classList.add("hidden");
    const actions = document.getElementById("scannerActionsGrid");
    if (actions) actions.classList.remove("hidden");
}

function setupReceiptScanner() {
    const btnOpen = document.getElementById("btnOpenReceiptScanner");
    const btnStartCamera = document.getElementById("btnStartCamera");
    const btnCloseCamera = document.getElementById("btnCloseCamera");
    const btnSnapPhoto = document.getElementById("btnSnapPhoto");
    const btnSwitchCamera = document.getElementById("btnSwitchCamera");
    const btnSelectFile = document.getElementById("btnSelectReceiptFile");
    const btnRetake = document.getElementById("btnRetakePhoto");
    
    const fileInput = document.getElementById("receiptFileInput");
    const cameraInput = document.getElementById("receiptCameraInput");
    const cameraVideo = document.getElementById("cameraVideo");
    const cameraCanvas = document.getElementById("cameraCanvas");
    const cameraWrap = document.getElementById("cameraViewportWrap");
    const actionsGrid = document.getElementById("scannerActionsGrid");
    const previewWrap = document.getElementById("receiptPreviewWrap");
    const previewImg = document.getElementById("receiptPreviewImg");
    const statusWrap = document.getElementById("scannerStatus");
    const resultBox = document.getElementById("scanResultBox");

    btnOpen.addEventListener("click", () => {
        openModal("modalReceiptScanner");
        stopCameraStream();
        previewWrap.classList.add("hidden");
        statusWrap.classList.add("hidden");
        resultBox.classList.add("hidden");
        actionsGrid.classList.remove("hidden");
    });

    async function startCamera() {
        stopCameraStream();
        previewWrap.classList.add("hidden");
        resultBox.classList.add("hidden");
        statusWrap.classList.add("hidden");

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            cameraInput.click();
            return;
        }

        try {
            const constraints = {
                video: {
                    facingMode: { ideal: currentFacingMode },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                },
                audio: false
            };
            activeCameraStream = await navigator.mediaDevices.getUserMedia(constraints);
            cameraVideo.srcObject = activeCameraStream;
            await cameraVideo.play();
            cameraWrap.classList.remove("hidden");
            actionsGrid.classList.add("hidden");
        } catch (err) {
            console.warn("Camera access failed, falling back to input capture:", err);
            cameraInput.click();
        }
    }

    btnStartCamera.addEventListener("click", startCamera);

    btnCloseCamera.addEventListener("click", () => {
        stopCameraStream();
    });

    btnSwitchCamera.addEventListener("click", () => {
        currentFacingMode = (currentFacingMode === "environment") ? "user" : "environment";
        startCamera();
    });

    btnSelectFile.addEventListener("click", () => fileInput.click());

    // Shutter button (capture photo from live video)
    btnSnapPhoto.addEventListener("click", () => {
        if (!cameraVideo.videoWidth) return;

        cameraCanvas.width = cameraVideo.videoWidth;
        cameraCanvas.height = cameraVideo.videoHeight;
        const ctx = cameraCanvas.getContext("2d");
        ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);

        cameraCanvas.toBlob(blob => {
            if (!blob) return;
            const file = new File([blob], `receipt_${Date.now()}.jpg`, { type: "image/jpeg" });
            const photoUrl = URL.createObjectURL(blob);
            previewImg.src = photoUrl;
            previewWrap.classList.remove("hidden");

            stopCameraStream();
            actionsGrid.classList.add("hidden");
            processReceipt(file);
        }, "image/jpeg", 0.92);
    });

    // Gallery file selected
    fileInput.addEventListener("change", (e) => {
        if (!e.target.files || !e.target.files[0]) return;
        const file = e.target.files[0];
        showSelectedFilePreview(file);
        processReceipt(file);
    });

    // Native camera fallback selected
    cameraInput.addEventListener("change", (e) => {
        if (!e.target.files || !e.target.files[0]) return;
        const file = e.target.files[0];
        showSelectedFilePreview(file);
        processReceipt(file);
    });

    function showSelectedFilePreview(file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
            previewImg.src = ev.target.result;
            previewWrap.classList.remove("hidden");
            actionsGrid.classList.add("hidden");
        };
        reader.readAsDataURL(file);
    }

    btnRetake.addEventListener("click", () => {
        stopCameraStream();
        previewWrap.classList.add("hidden");
        resultBox.classList.add("hidden");
        statusWrap.classList.add("hidden");
        actionsGrid.classList.remove("hidden");
        fileInput.value = "";
        cameraInput.value = "";
    });

    async function processReceipt(file) {
        statusWrap.classList.remove("hidden");
        resultBox.classList.add("hidden");

        const formData = new FormData();
        formData.append("user_id", state.userId);
        formData.append("auto_save", "true");
        formData.append("file", file);

        try {
            const res = await fetch("/api/receipts/scan", {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            statusWrap.classList.add("hidden");

            if (res.ok && data.success) {
                const d = data.data;
                document.getElementById("resStore").textContent = cleanText(d.store_name) || "Do'kon";
                document.getElementById("resAmount").textContent = `${formatNumber(d.total_amount)} so'm`;
                document.getElementById("resCategory").textContent = cleanText(d.category) || "Oziq-ovqat";
                document.getElementById("resItems").textContent = cleanText(d.items_summary) || cleanText(d.description) || "-";
                resultBox.classList.remove("hidden");

                showToast("Chek saqlandi");
                await refreshDashboard();
                await loadTransactions();
                await loadBudgets();
            } else {
                alert(data.message || "Chekni o'qib bo'lmadi");
            }
        } catch (e) {
            statusWrap.classList.add("hidden");
            alert("Skanerlashda xatolik yuz berdi");
        }
    }
}

function setupSmartInput() {
    const btnOpen = document.getElementById("btnOpenSmartInput");
    const textInput = document.getElementById("smartTextInput");
    const micBtn = document.getElementById("btnVoiceRecord");
    const submitBtn = document.getElementById("btnSubmitSmart");

    btnOpen.addEventListener("click", () => openModal("modalSmartInput"));

    let recognition = null;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = "uz-UZ";
        recognition.continuous = false;

        recognition.onstart = () => {
            state.isRecordingVoice = true;
            micBtn.style.background = "#B91C1C";
            micBtn.style.color = "#fff";
        };

        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            textInput.value = (textInput.value ? textInput.value + " " : "") + transcript;
        };

        recognition.onend = () => {
            state.isRecordingVoice = false;
            micBtn.style.background = "";
            micBtn.style.color = "";
        };
    }

    micBtn.addEventListener("click", () => {
        if (!recognition) {
            alert("Brauzeringiz ovoz bilan yozishni qo'llab-quvvatlamaydi. Iltimos, matn shaklida yozing!");
            return;
        }
        if (state.isRecordingVoice) recognition.stop();
        else recognition.start();
    });

    submitBtn.addEventListener("click", async () => {
        const text = textInput.value.trim();
        if (!text) return;

        submitBtn.disabled = true;
        submitBtn.textContent = "AI tahlil qilmoqda...";

        try {
            const res = await fetch("/api/ai/parse-text", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: state.userId,
                    text: text,
                    auto_save: true
                })
            });

            if (res.ok) {
                showToast("Amal saqlandi");
                textInput.value = "";
                closeModal("modalSmartInput");
                await refreshAll();
            }
        } catch (e) {
            showToast("Xatolik");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Saqlash";
        }
    });
}

function setupDebtAndBudgetForms() {
    document.getElementById("btnNewDebt").addEventListener("click", () => openModal("modalAddDebt"));
    document.getElementById("btnNewBudget").addEventListener("click", () => openModal("modalSetBudget"));

    const givenBtn = document.getElementById("btnDebtGiven");
    const takenBtn = document.getElementById("btnDebtTaken");

    givenBtn.addEventListener("click", () => {
        givenBtn.classList.add("active");
        takenBtn.classList.remove("active");
        state.selectedDebtType = "given";
    });

    takenBtn.addEventListener("click", () => {
        takenBtn.classList.add("active");
        givenBtn.classList.remove("active");
        state.selectedDebtType = "taken";
    });

    document.getElementById("btnSaveDebt").addEventListener("click", async () => {
        const name = cleanText(document.getElementById("debtPersonName").value);
        const amt = parseFloat(document.getElementById("debtAmount").value);
        const desc = cleanText(document.getElementById("debtDescription").value);

        if (!name || !amt) return;

        try {
            const res = await fetch("/api/debts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: state.userId,
                    person_name: name,
                    debt_type: state.selectedDebtType,
                    amount: amt,
                    description: desc
                })
            });

            if (res.ok) {
                showToast("Qarz saqlandi");
                closeModal("modalAddDebt");
                document.getElementById("debtPersonName").value = "";
                document.getElementById("debtAmount").value = "";
                document.getElementById("debtDescription").value = "";
                loadDebts();
            }
        } catch (e) {
            showToast("Xatolik");
        }
    });

    document.getElementById("btnSaveBudget").addEventListener("click", async () => {
        const cat = cleanText(document.getElementById("budgetCategorySelect").value);
        const limit = parseFloat(document.getElementById("budgetLimitAmount").value);

        if (!limit) return;

        try {
            const res = await fetch("/api/budgets", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: state.userId,
                    category: cat,
                    monthly_limit: limit
                })
            });

            if (res.ok) {
                showToast("Limit saqlandi");
                closeModal("modalSetBudget");
                document.getElementById("budgetLimitAmount").value = "";
                loadBudgets();
            }
        } catch (e) {
            showToast("Xatolik");
        }
    });
}

// ==================== AI CHAT SYSTEM ====================
function openAIChat() {
    document.getElementById("aiChatScreen").classList.add("active");
    document.body.style.overflow = "hidden";
}

function closeAIChat() {
    document.getElementById("aiChatScreen").classList.remove("active");
    document.body.style.overflow = "";
}

function addUserBubble(text) {
    const container = document.getElementById("aiChatMessages");
    const bubble = document.createElement("div");
    bubble.className = "ai-msg-bubble user";
    bubble.textContent = text;
    container.appendChild(bubble);
    scrollChatToBottom();
}

function addLoadingBubble() {
    const container = document.getElementById("aiChatMessages");
    const bubble = document.createElement("div");
    bubble.className = "ai-msg-bubble ai";
    bubble.id = "aiLoadingBubble";
    bubble.innerHTML = `<div class="ai-loading-dots"><span></span><span></span><span></span></div>`;
    container.appendChild(bubble);
    scrollChatToBottom();
    return bubble;
}

function removeLoadingBubble() {
    const el = document.getElementById("aiLoadingBubble");
    if (el) el.remove();
}

function addAIBubble(content) {
    const container = document.getElementById("aiChatMessages");
    const bubble = document.createElement("div");
    bubble.className = "ai-msg-bubble ai";
    bubble.innerHTML = content;
    container.appendChild(bubble);
    scrollChatToBottom();
}

function scrollChatToBottom() {
    const container = document.getElementById("aiChatMessages");
    requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight;
    });
}

function parseAIResponseToHTML(text) {
    const clean = cleanText(text);
    const lines = clean.split("\n").filter(l => l.trim());
    
    // Detect structured bullet points
    const bulletColors = ["red", "amber", "green", "blue", "red", "amber"];
    let bulletItems = [];
    let heading = "";
    let plainText = [];
    
    lines.forEach((line, i) => {
        const trimmed = line.trim();
        // Check for heading-like lines (short, no period at end, first line)
        if (i === 0 && trimmed.length < 60 && !trimmed.endsWith(".")) {
            heading = trimmed;
            return;
        }
        
        // Check for bullet patterns: - text, * text, • text, 1. text, numbered
        const bulletMatch = trimmed.match(/^[-*•●]\s*(.+)$/) || trimmed.match(/^\d+[.)]\s*(.+)$/);
        if (bulletMatch) {
            const bulletText = bulletMatch[1];
            // Try to split into title: description
            const colonSplit = bulletText.match(/^(.+?)[:\-–—]\s*(.+)$/);
            if (colonSplit) {
                bulletItems.push({ title: colonSplit[1].trim(), desc: colonSplit[2].trim() });
            } else {
                bulletItems.push({ title: bulletText, desc: "" });
            }
        } else {
            plainText.push(trimmed);
        }
    });
    
    // Build HTML
    let html = "";
    
    if (heading) {
        html += `<div class="ai-bubble-heading">${heading}</div>`;
    }
    
    if (bulletItems.length > 0) {
        bulletItems.forEach((item, idx) => {
            const color = bulletColors[idx % bulletColors.length];
            html += `<div class="ai-bullet-item">
                <div class="ai-bullet-dot ${color}"></div>
                <div class="ai-bullet-content">
                    <div class="ai-bullet-title">${item.title}</div>
                    ${item.desc ? `<div class="ai-bullet-desc">${item.desc}</div>` : ""}
                </div>
            </div>`;
        });
    }
    
    if (plainText.length > 0) {
        html += `<div style="margin-top:${bulletItems.length > 0 ? '10px' : '0'};font-size:14px;line-height:1.55;color:#0F172A;">${plainText.join("<br>")}</div>`;
    }
    
    // Fallback if nothing was parsed
    if (!html) {
        html = `<div style="font-size:14px;line-height:1.55;color:#0F172A;">${clean.replace(/\n/g, "<br>")}</div>`;
    }
    
    return html;
}

async function sendAIChatQuery(queryType, displayText) {
    const sendBtn = document.getElementById("aiChatSendBtn");
    sendBtn.disabled = true;
    
    // Show user message
    addUserBubble(displayText);
    
    // Show loading
    addLoadingBubble();
    
    try {
        const res = await fetch("/api/ai/advice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                user_id: state.userId,
                query_type: queryType,
                query_text: displayText
            })
        });
        
        removeLoadingBubble();
        
        if (res.ok) {
            const data = await res.json();
            const htmlContent = parseAIResponseToHTML(data.advice);
            addAIBubble(htmlContent);
        } else {
            addAIBubble(`<div style="color:#EF4444;font-size:14px;">Tahlil olishda xatolik yuz berdi. Qaytadan urinib ko'ring.</div>`);
        }
    } catch (e) {
        removeLoadingBubble();
        addAIBubble(`<div style="color:#EF4444;font-size:14px;">Server bilan aloqa uzildi.</div>`);
    } finally {
        sendBtn.disabled = false;
    }
}

// ==================== MODALS UTILITY ====================
function setupModalHandlers() {
    document.querySelectorAll("[data-close]").forEach(el => {
        el.addEventListener("click", () => {
            const modalId = el.dataset.close;
            closeModal(modalId);
        });
    });

    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.classList.remove("active");
                if (overlay.id === "modalReceiptScanner") {
                    stopCameraStream();
                }
            }
        });
    });
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("active");
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("active");
    if (id === "modalReceiptScanner") {
        stopCameraStream();
    }
}

// ==================== HELPERS ====================
function formatNumber(num) {
    if (!num) return "0";
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
        const d = new Date(dateStr);
        const day = String(d.getDate()).padStart(2, "0");
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const hour = String(d.getHours()).padStart(2, "0");
        const min = String(d.getMinutes()).padStart(2, "0");
        return `${day}.${month}, ${hour}:${min}`;
    } catch {
        return dateStr;
    }
}

function showToast(msg) {
    const toast = document.createElement("div");
    toast.className = "toast-msg";
    toast.textContent = cleanText(msg);
    DOM.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 320);
    }, 2400);
}
