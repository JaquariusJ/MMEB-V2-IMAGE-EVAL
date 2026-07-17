# Budget Execution Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `我的支出 > 支出分析` so it compares planned budgets from `fixed_expenses` with actual spending from `actual_expenses`.

**Architecture:** Add focused DTOs and mapper queries for budget execution analytics, expose them through `/api/expense-analytics`, mirror the same contract in the fallback Node API, then update the Vue expense analysis page to show summary cards, monthly trend, category execution, and unbudgeted spending. Keep the existing menu and existing planned-expense endpoints intact.

**Tech Stack:** Spring Boot 3, MyBatis XML mappers, MySQL, Vue 3, Ant Design Vue, existing chart components, fallback Node API in `dev-tools/mysql-api-server.cjs`.

---

### Task 1: Backend Execution Analytics Contract

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseExecutionSummaryResponse.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseExecutionCategoryRow.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseExecutionMonthlyPoint.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseUnbudgetedCategoryRow.java`
- Modify: `backend/src/main/java/com/example/assetmanager/mapper/FixedExpenseMapper.java`
- Modify: `backend/src/main/java/com/example/assetmanager/service/FixedExpenseService.java`
- Modify: `backend/src/main/java/com/example/assetmanager/controller/ExpenseAnalyticsController.java`
- Modify: `backend/src/main/resources/mapper/FixedExpenseMapper.xml`

- [ ] **Step 1: Write mapper/service-facing tests or compile checks first**

Run: `mvn -q -pl backend test`

Expected before implementation: compilation fails once controller/service references missing DTOs or mapper methods are introduced.

- [ ] **Step 2: Add DTOs and mapper method signatures**

Add DTO fields for yearly summary, month summary, category rows, unbudgeted rows, and monthly trend rows.

- [ ] **Step 3: Add MyBatis queries**

Add SQL that aggregates monthly budget from `fixed_expenses`, actual spending from `actual_expenses`, rolls categories by `PARENT` or `SUB`, and derives status.

- [ ] **Step 4: Add service normalization and endpoints**

Add `executionSummary(year, month, level)` and `executionMonthlyTrend(year, level)` to `FixedExpenseService`, then expose:

```text
GET /api/expense-analytics/execution-summary
GET /api/expense-analytics/execution-monthly-trend
```

- [ ] **Step 5: Run backend verification**

Run: `mvn -q -pl backend test`

Expected: tests compile and pass when Java 17 is available.

### Task 2: Fallback Node API Contract

**Files:**
- Modify: `dev-tools/mysql-api-server.cjs`

- [ ] **Step 1: Verify current syntax before edits**

Run: `node --check dev-tools/mysql-api-server.cjs`

Expected: syntax passes before changes.

- [ ] **Step 2: Implement execution helpers**

Add Node equivalents for execution summary and monthly trend using the same request/response shape as the Spring API.

- [ ] **Step 3: Wire routes**

Add route handlers for:

```text
GET /api/expense-analytics/execution-summary
GET /api/expense-analytics/execution-monthly-trend
```

- [ ] **Step 4: Run syntax verification**

Run: `node --check dev-tools/mysql-api-server.cjs`

Expected: syntax passes.

### Task 3: Frontend Budget Execution View

**Files:**
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/ExpenseStats.vue`
- Modify: `frontend/src/components/ExpenseReport.vue`
- Modify: `frontend/src/styles/base.css`

- [ ] **Step 1: Verify current frontend build**

Run: `npm --prefix frontend run build`

Expected before changes: current frontend builds or existing unrelated failures are noted.

- [ ] **Step 2: Add API client methods**

Add `executionSummary(params)` and `executionMonthlyTrend(params)` under `expenseAnalyticsApi`.

- [ ] **Step 3: Update App state and loading**

Load execution summary and monthly trend for selected year/month/level. Keep existing fixed expense and actual expense loading intact.

- [ ] **Step 4: Update presentation components**

Show yearly cards, current month cards, monthly trend, category execution table, and unbudgeted spending list.

- [ ] **Step 5: Run frontend build**

Run: `npm --prefix frontend run build`

Expected: build passes.

### Task 4: End-to-End Verification

**Files:**
- No new files unless a small verification script is needed.

- [ ] **Step 1: Run static checks**

Run:

```text
node --check dev-tools/mysql-api-server.cjs
npm --prefix frontend run build
```

- [ ] **Step 2: Start the available local stack if practical**

Use the existing fallback Node API plus Vite path when Java 17 is unavailable.

- [ ] **Step 3: Verify API shape**

Call the new execution endpoints and confirm they return yearly/month/category/unbudgeted data.

- [ ] **Step 4: Verify browser-visible UI**

Open the frontend and confirm `我的支出 > 支出分析` shows budget execution content without adding a new menu item.
