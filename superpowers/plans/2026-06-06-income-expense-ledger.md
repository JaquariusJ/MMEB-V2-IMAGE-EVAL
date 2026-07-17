# 收支流水与收入统计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing expense module into a unified income/expense ledger across backend, web, and iOS/mobile, with monthly income, expense, and balance statistics.

**Architecture:** Keep existing `Expense`-named backend APIs and tables for compatibility, and add `transactionType` / `categoryType` fields to distinguish income from expense. Existing budget-plan logic remains expense-only. Web and mobile consume the same API fields and filter categories by type.

**Tech Stack:** Java 17, Spring Boot 3.3.5, MyBatis, MySQL 8, Vue 3, Vite, Ant Design Vue, shared mobile Vue components.

---

## Local Commands

Run Java/Maven commands from repo root because `.mvn/maven.config` uses `.mvn/settings.xml`.

```bash
export JAVA_HOME=/Users/wujian/env/jdk17/jdk-17.0.16.jdk/Contents/Home
export PATH=/Users/wujian/env/apache-maven-3.9.4/bin:$JAVA_HOME/bin:$PATH
mvn -pl backend test
cd frontend-web && npm run build
cd frontend-ios && npm run build
```

## File Map

- Modify `backend/src/main/java/com/example/assetmanager/domain/ActualExpense.java`: add `transactionType`.
- Modify `backend/src/main/java/com/example/assetmanager/domain/ExpenseCategory.java`: add `categoryType`.
- Create `backend/src/main/java/com/example/assetmanager/domain/TransactionType.java`: enum with `EXPENSE` and `INCOME`.
- Modify `backend/src/main/java/com/example/assetmanager/dto/ActualExpenseRequest.java`: accept `transactionType`.
- Modify `backend/src/main/java/com/example/assetmanager/dto/ActualExpenseView.java`: return `transactionType`.
- Modify `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryRequest.java`: accept `categoryType`.
- Modify `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryView.java`: return `categoryType`.
- Create `backend/src/main/java/com/example/assetmanager/dto/CashflowSummaryResponse.java`: income, expense, balance.
- Create `backend/src/main/java/com/example/assetmanager/dto/CashflowMonthlyPoint.java`: monthly income, expense, balance trend.
- Create `backend/src/main/java/com/example/assetmanager/dto/CashflowCategoryPoint.java`: typed category distribution.
- Modify `backend/src/main/java/com/example/assetmanager/controller/ActualExpenseController.java`: add `transactionType` query parameter.
- Modify `backend/src/main/java/com/example/assetmanager/controller/ExpenseCategoryController.java`: add `categoryType` query parameter.
- Modify `backend/src/main/java/com/example/assetmanager/controller/ExpenseAnalyticsController.java`: add cashflow endpoints.
- Modify `backend/src/main/java/com/example/assetmanager/service/ActualExpenseService.java`: validate category type and apply transaction type.
- Modify `backend/src/main/java/com/example/assetmanager/service/ExpenseCategoryService.java`: type-aware category create/update/list/delete.
- Modify `backend/src/main/java/com/example/assetmanager/service/FixedExpenseService.java`: reject income categories for budgets.
- Modify `backend/src/main/java/com/example/assetmanager/config/AuthSchemaInitializer.java`: idempotent DDL for new columns, indexes, default income categories.
- Modify `backend/src/main/resources/mapper/ActualExpenseMapper.xml`: map new field and add cashflow SQL.
- Modify `backend/src/main/resources/mapper/ExpenseCategoryMapper.xml`: map/filter category type and unique lookup.
- Modify `backend/src/main/resources/mapper/FixedExpenseMapper.xml`: only count `EXPENSE` transactions in budget execution SQL.
- Add `database/migrations/2026-06-06-add-income-expense-ledger.sql`: explicit DB migration.
- Modify backend tests in `backend/src/test/java/com/example/assetmanager/service/*.java`: restore compile and add behavior coverage.
- Modify `shared/src/api/client.js`: pass type filters to existing APIs and add cashflow analytics methods.
- Modify `shared/src/components/ActualExpenseManager.vue`: become typed 收支流水 UI.
- Modify `shared/src/components/ExpenseCategoryManager.vue`: type switch for 收支分类.
- Modify `shared/src/components/FixedExpenseManager.vue`: receive expense-only categories.
- Modify `shared/src/components/ExpenseStats.vue` and `shared/src/components/ExpenseReport.vue`: add 收支 metrics while preserving budget execution.
- Modify `shared/src/components/MobileFinanceApp.vue`: add mobile income/expense type controls, stats, colors, category filtering, text updates.
- Modify `frontend-web/src/App.vue`: rename navigation, wire cashflow data, filter categories by type, refresh related data.
- Modify `AGENTS.md`: add any new stable commands or naming notes discovered during implementation.

---

### Task 1: Restore Backend Test Baseline

**Files:**
- Modify: `backend/src/test/java/com/example/assetmanager/service/ExpenseCategoryServiceTest.java`
- Modify: `backend/src/test/java/com/example/assetmanager/service/FixedExpenseServiceTest.java`

- [ ] **Step 1: Reproduce current test compile failure**

Run:

```bash
export JAVA_HOME=/Users/wujian/env/jdk17/jdk-17.0.16.jdk/Contents/Home
export PATH=/Users/wujian/env/apache-maven-3.9.4/bin:$JAVA_HOME/bin:$PATH
mvn -pl backend test
```

Expected: FAIL during `testCompile` because `ExpenseCategoryServiceTest` calls an old constructor and `FakeFixedExpenseMapper` lacks `deleteByCategoryId`.

- [ ] **Step 2: Fix `ExpenseCategoryServiceTest` fakes**

Update service construction to pass all three constructor args:

```java
FakeExpenseCategoryMapper categoryMapper = new FakeExpenseCategoryMapper();
FakeActualExpenseMapper actualMapper = new FakeActualExpenseMapper();
FakeFixedExpenseMapper fixedMapper = new FakeFixedExpenseMapper();
ExpenseCategoryService service = new ExpenseCategoryService(categoryMapper, actualMapper, fixedMapper);
```

Add minimal fake mapper classes in the test:

```java
private static class FakeActualExpenseMapper implements ActualExpenseMapper {
    @Override public List<ActualExpenseView> findAll(String startDate, String endDate, Long categoryId) { return List.of(); }
    @Override public ActualExpense findById(Long id) { return null; }
    @Override public void insert(ActualExpense expense) {}
    @Override public void update(ActualExpense expense) {}
    @Override public void delete(Long id) {}
    @Override public void deleteByCategoryId(Long categoryId) {}
}

private static class FakeFixedExpenseMapper implements FixedExpenseMapper {
    @Override public List<FixedExpenseView> findAll(Integer expenseYear, Long categoryId, String period) { return List.of(); }
    @Override public FixedExpense findById(Long id) { return null; }
    @Override public FixedExpense findCopyConflict(Integer expenseYear, String name, Long categoryId, String period, Integer startMonth, Integer endMonth) { return null; }
    @Override public void insert(FixedExpense expense) {}
    @Override public void update(FixedExpense expense) {}
    @Override public void delete(Long id) {}
    @Override public void deleteByCategoryId(Long categoryId) {}
    @Override public List<ExpenseCategoryStats> statsByCategory(Integer expenseYear, String categoryLevel) { return List.of(); }
    @Override public List<ExpenseYearlyTrend> yearlyTrend() { return List.of(); }
    @Override public List<ExpenseMonthlyTrendPoint> monthlyTrend(Integer expenseYear, String categoryLevel) { return List.of(); }
    @Override public ExpenseExecutionSummaryResponse executionSummary(Integer expenseYear, Integer month, String categoryLevel) { return null; }
    @Override public List<ExpenseExecutionCategoryRow> executionCategories(Integer expenseYear, String categoryLevel) { return List.of(); }
    @Override public List<ExpenseUnbudgetedCategoryRow> executionUnbudgetedCategories(Integer expenseYear, String categoryLevel) { return List.of(); }
    @Override public List<ExpenseExecutionMonthlyPoint> executionMonthlyTrend(Integer expenseYear, String categoryLevel) { return List.of(); }
}
```

- [ ] **Step 3: Fix `FixedExpenseServiceTest.FakeFixedExpenseMapper`**

Add the missing method:

```java
@Override
public void deleteByCategoryId(Long categoryId) {
}
```

- [ ] **Step 4: Verify baseline passes before feature work**

Run:

```bash
mvn -pl backend test
```

Expected: PASS. If any old test fails, fix only the test baseline mismatch before continuing.

- [ ] **Step 5: Commit**

```bash
git add backend/src/test/java/com/example/assetmanager/service/ExpenseCategoryServiceTest.java backend/src/test/java/com/example/assetmanager/service/FixedExpenseServiceTest.java
git commit -m "test: restore backend service test baseline"
```

---

### Task 2: Add Typed Domain Model and Service Tests

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/domain/TransactionType.java`
- Modify: `backend/src/main/java/com/example/assetmanager/domain/ActualExpense.java`
- Modify: `backend/src/main/java/com/example/assetmanager/domain/ExpenseCategory.java`
- Modify: `backend/src/main/java/com/example/assetmanager/dto/ActualExpenseRequest.java`
- Modify: `backend/src/main/java/com/example/assetmanager/dto/ActualExpenseView.java`
- Modify: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryRequest.java`
- Modify: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryView.java`
- Modify: `backend/src/test/java/com/example/assetmanager/service/ExpenseCategoryServiceTest.java`
- Create: `backend/src/test/java/com/example/assetmanager/service/ActualExpenseServiceTest.java`

- [ ] **Step 1: Write failing tests for type defaults and category-type validation**

Create `ActualExpenseServiceTest.java` with tests:

```java
@Test
void createDefaultsToExpenseAndAcceptsExpenseCategory() {
    FakeActualExpenseMapper actualMapper = new FakeActualExpenseMapper();
    FakeExpenseCategoryMapper categoryMapper = new FakeExpenseCategoryMapper();
    categoryMapper.category = category(1L, 10L, TransactionType.EXPENSE);
    ActualExpenseService service = new ActualExpenseService(actualMapper, categoryMapper);

    ActualExpense saved = service.create(request(null, 1L, "88.00"));

    assertThat(actualMapper.inserted.getTransactionType()).isEqualTo(TransactionType.EXPENSE);
    assertThat(saved.getTransactionType()).isEqualTo(TransactionType.EXPENSE);
}

@Test
void createRejectsIncomeWithExpenseCategory() {
    FakeActualExpenseMapper actualMapper = new FakeActualExpenseMapper();
    FakeExpenseCategoryMapper categoryMapper = new FakeExpenseCategoryMapper();
    categoryMapper.category = category(1L, 10L, TransactionType.EXPENSE);
    ActualExpenseService service = new ActualExpenseService(actualMapper, categoryMapper);

    assertThatThrownBy(() -> service.create(request(TransactionType.INCOME, 1L, "5000.00")))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessage("请选择收入分类");
}
```

Extend `ExpenseCategoryServiceTest` with:

```java
@Test
void createDefaultsCategoryTypeToExpense() {
    ExpenseCategoryRequest request = request("Daily", " ");
    FakeExpenseCategoryMapper mapper = new FakeExpenseCategoryMapper();
    ExpenseCategoryService service = new ExpenseCategoryService(mapper, new FakeActualExpenseMapper(), new FakeFixedExpenseMapper());

    ExpenseCategory result = service.create(request);

    assertThat(result.getCategoryType()).isEqualTo(TransactionType.EXPENSE);
}

@Test
void createRejectsChildWithDifferentParentType() {
    ExpenseCategoryRequest request = request("Salary Detail", "CircleDollarSign");
    request.setCategoryType(TransactionType.INCOME);
    request.setParentId(1L);
    FakeExpenseCategoryMapper mapper = new FakeExpenseCategoryMapper();
    ExpenseCategory parent = new ExpenseCategory();
    parent.setId(1L);
    parent.setCategoryType(TransactionType.EXPENSE);
    mapper.category = parent;
    ExpenseCategoryService service = new ExpenseCategoryService(mapper, new FakeActualExpenseMapper(), new FakeFixedExpenseMapper());

    assertThatThrownBy(() -> service.create(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessage("子分类类型必须和大类一致");
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
mvn -pl backend test -Dtest=ActualExpenseServiceTest,ExpenseCategoryServiceTest
```

Expected: FAIL because `TransactionType`, `transactionType`, and `categoryType` do not exist yet.

- [ ] **Step 3: Add enum and fields**

Create `TransactionType.java`:

```java
package com.example.assetmanager.domain;

public enum TransactionType {
    EXPENSE,
    INCOME
}
```

Add fields, getters, and setters:

```java
private TransactionType transactionType;
public TransactionType getTransactionType() { return transactionType; }
public void setTransactionType(TransactionType transactionType) { this.transactionType = transactionType; }
```

Use `transactionType` on `ActualExpense` and `categoryType` on `ExpenseCategory`, `ExpenseCategoryRequest`, and `ExpenseCategoryView`.

- [ ] **Step 4: Update service normalization**

In `ActualExpenseService.applyRequest`:

```java
TransactionType type = request.getTransactionType() == null ? TransactionType.EXPENSE : request.getTransactionType();
expense.setTransactionType(type);
```

In `ActualExpenseService.validateCategory`:

```java
private void validateCategory(Long categoryId, TransactionType transactionType) {
    ExpenseCategory category = categoryId == null ? null : expenseCategoryMapper.findById(categoryId);
    if (category == null) {
        throw new IllegalArgumentException(transactionType == TransactionType.INCOME ? "请选择收入分类" : "请选择支出分类");
    }
    if (category.getCategoryType() != transactionType) {
        throw new IllegalArgumentException(transactionType == TransactionType.INCOME ? "请选择收入分类" : "请选择支出分类");
    }
}
```

Call it from create/update after normalizing type.

In `ExpenseCategoryService`, normalize request type:

```java
private TransactionType normalizeCategoryType(TransactionType type) {
    return type == null ? TransactionType.EXPENSE : type;
}
```

Set category type on create. On update, keep existing type and reject type changes:

```java
if (request.getCategoryType() != null && request.getCategoryType() != existing.getCategoryType()) {
    throw new IllegalArgumentException("分类类型不能修改");
}
```

When parent exists:

```java
if (parent.getCategoryType() != categoryType) {
    throw new IllegalArgumentException("子分类类型必须和大类一致");
}
```

- [ ] **Step 5: Verify tests pass**

Run:

```bash
mvn -pl backend test -Dtest=ActualExpenseServiceTest,ExpenseCategoryServiceTest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/example/assetmanager/domain backend/src/main/java/com/example/assetmanager/dto backend/src/main/java/com/example/assetmanager/service backend/src/test/java/com/example/assetmanager/service
git commit -m "feat: add typed income expense domain"
```

---

### Task 3: Add Database Migration, Mapper Fields, and Filters

**Files:**
- Add: `database/migrations/2026-06-06-add-income-expense-ledger.sql`
- Modify: `database/schema.sql`
- Modify: `backend/src/main/java/com/example/assetmanager/config/AuthSchemaInitializer.java`
- Modify: `backend/src/main/java/com/example/assetmanager/mapper/ActualExpenseMapper.java`
- Modify: `backend/src/main/java/com/example/assetmanager/mapper/ExpenseCategoryMapper.java`
- Modify: `backend/src/main/java/com/example/assetmanager/controller/ActualExpenseController.java`
- Modify: `backend/src/main/java/com/example/assetmanager/controller/ExpenseCategoryController.java`
- Modify: `backend/src/main/resources/mapper/ActualExpenseMapper.xml`
- Modify: `backend/src/main/resources/mapper/ExpenseCategoryMapper.xml`

- [ ] **Step 1: Add explicit migration**

Create `database/migrations/2026-06-06-add-income-expense-ledger.sql`:

```sql
use asset_manager;

alter table actual_expenses
  add column transaction_type varchar(20) not null default 'EXPENSE' after expense_date;

alter table expense_categories
  add column category_type varchar(20) not null default 'EXPENSE' after parent_id;

drop index uk_expense_categories_user_parent_name on expense_categories;

create unique index uk_expense_categories_user_type_parent_name
  on expense_categories (user_id, category_type, parent_id, name);

create index idx_actual_expenses_user_type_date
  on actual_expenses (user_id, transaction_type, expense_date);

insert into expense_categories (user_id, parent_id, category_type, name, icon, remark, created_by, updated_by)
select u.id, null, 'INCOME', v.name, 'Banknote', v.remark, 'system', 'system'
from app_users u
join (
  select '工资' as name, '工资收入' as remark union all
  select '奖金', '奖金收入' union all
  select '理财收益', '投资与理财收入' union all
  select '副业', '副业收入' union all
  select '红包转账', '红包、转账与人情收入' union all
  select '其他收入', '其他收入'
) v
where not exists (
  select 1 from expense_categories c
  where c.user_id = u.id and c.category_type = 'INCOME' and c.parent_id is null and c.name = v.name
);
```

If running against a DB where columns may already exist, run equivalent `alter` statements manually with guards or rely on `AuthSchemaInitializer` after deployment.

- [ ] **Step 2: Update schema and initializer**

Update `database/schema.sql` create table statements to include:

```sql
category_type varchar(20) not null default 'EXPENSE',
transaction_type varchar(20) not null default 'EXPENSE',
```

In `AuthSchemaInitializer`, add:

```java
addColumn(jdbcTemplate, "actual_expenses", "transaction_type varchar(20) not null default 'EXPENSE' after expense_date");
addColumn(jdbcTemplate, "expense_categories", "category_type varchar(20) not null default 'EXPENSE' after parent_id");
dropIndexIfExists(jdbcTemplate, "expense_categories", "uk_expense_categories_user_parent_name");
createIndexIfMissing(jdbcTemplate, "expense_categories", "uk_expense_categories_user_type_parent_name", "unique index uk_expense_categories_user_type_parent_name (user_id, category_type, parent_id, name)");
createIndexIfMissing(jdbcTemplate, "actual_expenses", "idx_actual_expenses_user_type_date", "index idx_actual_expenses_user_type_date (user_id, transaction_type, expense_date)");
ensureDefaultIncomeCategories(jdbcTemplate);
```

Add `ensureDefaultIncomeCategories` using the same six categories from the migration and `insert ... select ... where not exists`.

- [ ] **Step 3: Update mapper interfaces and controllers**

Change `ActualExpenseMapper.findAll` to:

```java
List<ActualExpenseView> findAll(@Param("startDate") String startDate,
                                @Param("endDate") String endDate,
                                @Param("categoryId") Long categoryId,
                                @Param("transactionType") String transactionType);
```

Change `ActualExpenseController.list` to accept:

```java
@RequestParam(required = false) String transactionType
```

Pass it to `service.list(startDate, endDate, categoryId, transactionType)`.

Change `ExpenseCategoryMapper.findAll` to:

```java
List<ExpenseCategoryView> findAll(@Param("categoryType") String categoryType);
```

Change `ExpenseCategoryController.list` to accept optional `categoryType`.

- [ ] **Step 4: Update XML mapping**

In `ActualExpenseMapper.xml`, map and write `transaction_type`:

```xml
<result column="transaction_type" property="transactionType"/>
```

Add to insert/update:

```xml
transaction_type,
#{transactionType},
transaction_type = #{transactionType},
```

Add list filter:

```xml
and (#{transactionType} is null or e.transaction_type = #{transactionType})
```

In `ExpenseCategoryMapper.xml`, map/filter `category_type`; update duplicate lookup to include type:

```xml
<result column="category_type" property="categoryType"/>
and (#{categoryType} is null or c.category_type = #{categoryType})
where user_id = #{currentUserId}
  and category_type = #{categoryType}
  and ((#{parentId} is null and parent_id is null) or parent_id = #{parentId})
  and name = #{name}
```

- [ ] **Step 5: Verify compile**

Run:

```bash
mvn -pl backend test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add database backend/src/main/java/com/example/assetmanager backend/src/main/resources/mapper
git commit -m "feat: persist typed income expense records"
```

---

### Task 4: Add Cashflow Analytics and Keep Budget Expense-Only

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/dto/CashflowSummaryResponse.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/CashflowMonthlyPoint.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/CashflowCategoryPoint.java`
- Modify: `backend/src/main/java/com/example/assetmanager/mapper/ActualExpenseMapper.java`
- Modify: `backend/src/main/resources/mapper/ActualExpenseMapper.xml`
- Modify: `backend/src/main/java/com/example/assetmanager/service/ActualExpenseService.java`
- Modify: `backend/src/main/java/com/example/assetmanager/controller/ExpenseAnalyticsController.java`
- Modify: `backend/src/main/resources/mapper/FixedExpenseMapper.xml`
- Create/modify: `backend/src/test/java/com/example/assetmanager/service/ActualExpenseServiceTest.java`

- [ ] **Step 1: Write failing service tests for cashflow summary**

Add to `ActualExpenseServiceTest`:

```java
@Test
void cashflowSummaryCalculatesBalance() {
    FakeActualExpenseMapper actualMapper = new FakeActualExpenseMapper();
    actualMapper.cashflowSummary = new CashflowSummaryResponse(
        new BigDecimal("8000.00"),
        new BigDecimal("3500.00")
    );
    ActualExpenseService service = new ActualExpenseService(actualMapper, new FakeExpenseCategoryMapper());

    CashflowSummaryResponse result = service.cashflowSummary(2026, 6);

    assertThat(result.getIncomeAmount()).isEqualByComparingTo("8000.00");
    assertThat(result.getExpenseAmount()).isEqualByComparingTo("3500.00");
    assertThat(result.getBalanceAmount()).isEqualByComparingTo("4500.00");
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
mvn -pl backend test -Dtest=ActualExpenseServiceTest
```

Expected: FAIL because `CashflowSummaryResponse` and `cashflowSummary` do not exist.

- [ ] **Step 3: Add DTOs**

Implement `CashflowSummaryResponse`:

```java
public class CashflowSummaryResponse {
    private BigDecimal incomeAmount = BigDecimal.ZERO;
    private BigDecimal expenseAmount = BigDecimal.ZERO;
    private BigDecimal balanceAmount = BigDecimal.ZERO;

    public CashflowSummaryResponse() {}
    public CashflowSummaryResponse(BigDecimal incomeAmount, BigDecimal expenseAmount) {
        this.incomeAmount = incomeAmount == null ? BigDecimal.ZERO : incomeAmount;
        this.expenseAmount = expenseAmount == null ? BigDecimal.ZERO : expenseAmount;
        this.balanceAmount = this.incomeAmount.subtract(this.expenseAmount);
    }
    // getters and setters recompute balance when both values are set by service
}
```

Implement `CashflowMonthlyPoint` with `month`, `incomeAmount`, `expenseAmount`, `balanceAmount`.

Implement `CashflowCategoryPoint` with `categoryId`, `categoryName`, `parentCategoryId`, `parentCategoryName`, `transactionType`, `amount`, `itemCount`.

- [ ] **Step 4: Add mapper/service/controller methods**

Mapper interface:

```java
CashflowSummaryResponse cashflowSummary(@Param("year") Integer year, @Param("month") Integer month);
List<CashflowMonthlyPoint> cashflowMonthlyTrend(@Param("year") Integer year);
List<CashflowCategoryPoint> cashflowCategoryDistribution(@Param("year") Integer year, @Param("month") Integer month, @Param("transactionType") String transactionType);
```

Service:

```java
public CashflowSummaryResponse cashflowSummary(Integer year, Integer month) {
    CashflowSummaryResponse response = actualExpenseMapper.cashflowSummary(normalizeYear(year), normalizeMonth(month));
    if (response == null) response = new CashflowSummaryResponse();
    response.recomputeBalance();
    return response;
}
```

Controller endpoints:

```java
@GetMapping("/cashflow-summary")
public CashflowSummaryResponse cashflowSummary(@RequestParam Integer year, @RequestParam Integer month) { ... }

@GetMapping("/cashflow-monthly-trend")
public List<CashflowMonthlyPoint> cashflowMonthlyTrend(@RequestParam Integer year) { ... }

@GetMapping("/cashflow-category-distribution")
public List<CashflowCategoryPoint> cashflowCategoryDistribution(@RequestParam Integer year, @RequestParam Integer month, @RequestParam String transactionType) { ... }
```

- [ ] **Step 5: Add SQL**

In `ActualExpenseMapper.xml`:

```sql
select
  coalesce(sum(case when transaction_type = 'INCOME' then amount else 0 end), 0) as income_amount,
  coalesce(sum(case when transaction_type = 'EXPENSE' then amount else 0 end), 0) as expense_amount
from actual_expenses
where user_id = #{currentUserId}
  and expense_date >= str_to_date(concat(#{year}, '-', lpad(#{month}, 2, '0'), '-01'), '%Y-%m-%d')
  and expense_date < date_add(str_to_date(concat(#{year}, '-', lpad(#{month}, 2, '0'), '-01'), '%Y-%m-%d'), interval 1 month)
```

For category distribution, group by category and `transaction_type`, joining parent categories.

- [ ] **Step 6: Make budget SQL expense-only**

In `FixedExpenseMapper.xml`, every subquery reading `actual_expenses a` for budget execution must include:

```sql
and a.transaction_type = 'EXPENSE'
```

This applies to yearly actual, month actual, execution categories, unbudgeted categories, and monthly trend actuals.

- [ ] **Step 7: Verify backend**

Run:

```bash
mvn -pl backend test
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/main/java/com/example/assetmanager backend/src/main/resources/mapper backend/src/test/java/com/example/assetmanager/service
git commit -m "feat: add cashflow analytics"
```

---

### Task 5: Update Web API Client and 收支流水 UI

**Files:**
- Modify: `shared/src/api/client.js`
- Modify: `shared/src/components/ActualExpenseManager.vue`
- Modify: `shared/src/styles/base.css`
- Modify: `frontend-web/src/App.vue`

- [ ] **Step 1: Add API methods**

Update `shared/src/api/client.js`:

```js
export const expenseCategoryApi = {
  list: (params = {}) => api.get('/expense-categories', { params }).then((res) => res.data),
  // existing methods unchanged
}

export const expenseAnalyticsApi = {
  // existing methods unchanged
  cashflowSummary: (params = {}) => api.get('/expense-analytics/cashflow-summary', { params }).then((res) => res.data),
  cashflowMonthlyTrend: (params = {}) => api.get('/expense-analytics/cashflow-monthly-trend', { params }).then((res) => res.data),
  cashflowCategoryDistribution: (params = {}) => api.get('/expense-analytics/cashflow-category-distribution', { params }).then((res) => res.data)
}
```

- [ ] **Step 2: Update `ActualExpenseManager.vue` props and filters**

Add transaction filter and summary props:

```js
const props = defineProps({
  expenses: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  filters: { type: Object, required: true },
  cashflowSummary: { type: Object, default: () => ({ incomeAmount: 0, expenseAmount: 0, balanceAmount: 0 }) }
})
```

Add filter control:

```vue
<label>
  类型
  <select v-model="filterTransactionType">
    <option value="">全部</option>
    <option value="INCOME">收入</option>
    <option value="EXPENSE">支出</option>
  </select>
</label>
```

Add metric cards:

```vue
<article class="metric-card net"><span>收入</span><strong>{{ money(cashflowSummary.incomeAmount) }}</strong></article>
<article class="metric-card liability"><span>支出</span><strong>{{ money(cashflowSummary.expenseAmount) }}</strong></article>
<article class="metric-card" :class="balanceClass"><span>结余</span><strong>{{ money(cashflowSummary.balanceAmount) }}</strong></article>
```

- [ ] **Step 3: Update form and table**

Add type column and form type selector:

```vue
<template v-else-if="column.key === 'transactionType'">{{ transactionTypeText(record.transactionType) }}</template>
<template v-else-if="column.key === 'amount'">
  <span class="amount-cell" :class="transactionAmountClass(record.transactionType)">
    {{ money(record.amount) }}
  </span>
</template>
```

Form field:

```vue
<a-form-item label="类型" required>
  <a-segmented v-model:value="form.transactionType" :options="transactionTypeOptions" />
</a-form-item>
```

When type changes:

```js
watch(() => form.transactionType, () => {
  form.parentCategoryId = undefined
  form.categoryId = undefined
})
```

- [ ] **Step 4: Wire `frontend-web/src/App.vue`**

Add state:

```js
const cashflowSummary = ref({ incomeAmount: 0, expenseAmount: 0, balanceAmount: 0 })
```

Update actual filters:

```js
const actualExpenseFilters = ref({
  startDate: `${nowMonth}-01`,
  endDate: `${nowMonth}-31`,
  categoryId: '',
  transactionType: ''
})
```

Load cashflow with actual expenses:

```js
const loadCashflowSummary = async () => {
  cashflowSummary.value = await expenseAnalyticsApi.cashflowSummary({
    year: Number(actualExpenseFilters.value.startDate.slice(0, 4)),
    month: Number(actualExpenseFilters.value.startDate.slice(5, 7))
  })
}
```

Pass prop:

```vue
<ActualExpenseManager
  :cashflow-summary="cashflowSummary"
/>
```

- [ ] **Step 5: Verify web build**

Run:

```bash
cd frontend-web && npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add shared/src/api/client.js shared/src/components/ActualExpenseManager.vue shared/src/styles/base.css frontend-web/src/App.vue
git commit -m "feat: update web cashflow ledger"
```

---

### Task 6: Update Web 收支分类, 预算计划, and 收支分析

**Files:**
- Modify: `shared/src/components/ExpenseCategoryManager.vue`
- Modify: `shared/src/components/FixedExpenseManager.vue`
- Modify: `shared/src/components/ExpenseStats.vue`
- Modify: `shared/src/components/ExpenseReport.vue`
- Modify: `frontend-web/src/App.vue`

- [ ] **Step 1: Add category type switch to category manager**

In `ExpenseCategoryManager.vue`, add a `categoryType` ref defaulting to `EXPENSE`:

```js
const categoryType = ref('EXPENSE')
const visibleCategories = computed(() => props.categories.filter((item) => (item.categoryType || 'EXPENSE') === categoryType.value))
```

Template:

```vue
<a-segmented v-model:value="categoryType" :options="[
  { label: '支出分类', value: 'EXPENSE' },
  { label: '收入分类', value: 'INCOME' }
]" />
```

On save payload:

```js
categoryType: categoryType.value
```

- [ ] **Step 2: Ensure budget only sees expense categories**

In `frontend-web/src/App.vue`, pass filtered categories:

```vue
<FixedExpenseManager :categories="expenseOnlyCategories" />
```

Computed:

```js
const expenseOnlyCategories = computed(() => expenseCategories.value.filter((item) => (item.categoryType || 'EXPENSE') === 'EXPENSE'))
```

- [ ] **Step 3: Rename navigation and messages**

Replace visible strings:

```text
我的支出 -> 我的收支
支出分析 -> 收支分析
支出计划 -> 预算计划
支出流水 -> 收支流水
支出分类 -> 收支分类
支出分类已保存 -> 收支分类已保存
支出流水已保存 -> 收支流水已保存
支出计划已保存 -> 预算计划已保存
```

Keep internal refs such as `expenseManageOpen` and view keys unchanged.

- [ ] **Step 4: Add cashflow metrics to analysis**

In analysis section, render:

```vue
<section class="metric-grid">
  <article class="metric-card net"><span>本月收入</span><strong>{{ money(cashflowSummary.incomeAmount) }}</strong></article>
  <article class="metric-card liability"><span>本月支出</span><strong>{{ money(cashflowSummary.expenseAmount) }}</strong></article>
  <article class="metric-card" :class="Number(cashflowSummary.balanceAmount || 0) >= 0 ? 'net' : 'liability'">
    <span>本月结余</span><strong>{{ money(cashflowSummary.balanceAmount) }}</strong>
  </article>
</section>
```

Change existing budget area heading to `预算执行`.

- [ ] **Step 5: Verify**

Run:

```bash
cd frontend-web && npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add shared/src/components/ExpenseCategoryManager.vue shared/src/components/FixedExpenseManager.vue shared/src/components/ExpenseStats.vue shared/src/components/ExpenseReport.vue frontend-web/src/App.vue
git commit -m "feat: update web cashflow analysis and categories"
```

---

### Task 7: Update iOS/Mobile 收支 Experience

**Files:**
- Modify: `shared/src/components/MobileFinanceApp.vue`
- Build: `frontend-ios`

- [ ] **Step 1: Add mobile state**

Extend `expenseForm`:

```js
const expenseForm = reactive({
  transactionType: 'EXPENSE',
  expenseDate: today(),
  parentCategoryId: '',
  categoryId: '',
  amount: '',
  merchant: '',
  sourceType: 'MANUAL',
  sourceText: '',
  sourceImageName: ''
})
```

Add computed filters:

```js
const activeTypeCategories = computed(() =>
  expenseCategories.value.filter((item) => (item.categoryType || 'EXPENSE') === expenseForm.transactionType)
)
const parentCategories = computed(() => activeTypeCategories.value.filter((item) => !item.parentId))
const leafCategories = computed(() => activeTypeCategories.value.filter((item) => item.parentId))
```

- [ ] **Step 2: Add monthly income/expense/balance totals**

Use loaded monthly records:

```js
const monthIncomeTotal = computed(() =>
  monthExpenses.value.filter((item) => item.transactionType === 'INCOME').reduce((sum, item) => sum + Number(item.amount || 0), 0)
)
const monthExpenseTotal = computed(() =>
  monthExpenses.value.filter((item) => (item.transactionType || 'EXPENSE') === 'EXPENSE').reduce((sum, item) => sum + Number(item.amount || 0), 0)
)
const monthBalanceTotal = computed(() => monthIncomeTotal.value - monthExpenseTotal.value)
```

- [ ] **Step 3: Update mobile sheet UI**

Add segmented type controls above amount:

```vue
<div class="mobile-segmented">
  <button type="button" :class="{ active: expenseForm.transactionType === 'EXPENSE' }" @click="setExpenseFormType('EXPENSE')">支出</button>
  <button type="button" :class="{ active: expenseForm.transactionType === 'INCOME' }" @click="setExpenseFormType('INCOME')">收入</button>
</div>
```

Add method:

```js
const setExpenseFormType = (type) => {
  if (expenseForm.transactionType === type) return
  expenseForm.transactionType = type
  expenseForm.parentCategoryId = ''
  expenseForm.categoryId = ''
}
```

- [ ] **Step 4: Preserve type when editing and inline editing**

In `openEdit`:

```js
transactionType: record.transactionType || 'EXPENSE',
```

In inline update payload:

```js
transactionType: record.transactionType || 'EXPENSE',
```

- [ ] **Step 5: Update labels and colors**

Visible text changes:

```text
支出排行榜 -> 收支排行榜 or 支出排行榜 for expense-only ranking
支出计划 -> 预算计划
还没有年度支出计划 -> 还没有年度预算计划
记账 -> 记一笔
```

For mixed ledgers, use:

```vue
<em :class="record.transactionType === 'INCOME' ? 'income-amount' : 'expense-amount'">{{ money(record.amount) }}</em>
```

- [ ] **Step 6: Verify mobile build**

Run:

```bash
cd frontend-ios && npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add shared/src/components/MobileFinanceApp.vue frontend-ios
git commit -m "feat: update mobile cashflow ledger"
```

---

### Task 8: End-to-End Verification and Local Service Smoke Test

**Files:**
- Modify if needed: `AGENTS.md`

- [ ] **Step 1: Run backend tests**

Run:

```bash
export JAVA_HOME=/Users/wujian/env/jdk17/jdk-17.0.16.jdk/Contents/Home
export PATH=/Users/wujian/env/apache-maven-3.9.4/bin:$JAVA_HOME/bin:$PATH
mvn -pl backend test
```

Expected: PASS.

- [ ] **Step 2: Run frontend builds**

Run:

```bash
cd frontend-web && npm run build
cd ../frontend-ios && npm run build
```

Expected: both PASS.

- [ ] **Step 3: Start backend and web**

Run from repo root:

```bash
export JAVA_HOME=/Users/wujian/env/jdk17/jdk-17.0.16.jdk/Contents/Home
export PATH=/Users/wujian/env/apache-maven-3.9.4/bin:$JAVA_HOME/bin:$PATH
mvn -pl backend -Dmaven.test.skip=true spring-boot:run
```

In another terminal:

```bash
cd frontend-web && npm run dev -- --host 127.0.0.1
```

Expected:

- backend listens on `http://127.0.0.1:8080`
- web listens on `http://127.0.0.1:5173`
- backend connects to remote MySQL `101.33.233.232:3578`

- [ ] **Step 4: Browser QA checklist**

Open `http://127.0.0.1:5173/` and verify:

- “我的收支” menu appears.
- “收支流水” opens.
- Add an income record with income category and positive amount.
- Add an expense record with expense category and positive amount.
- Income row amount is green.
- Expense row amount is red.
- Monthly income, expense, and balance update.
- “预算计划” category picker does not show income categories.
- “收支分类” can switch between income and expense categories.

- [ ] **Step 5: API smoke checks**

Run:

```bash
curl -sS 'http://127.0.0.1:8080/api/expense-analytics/cashflow-summary?year=2026&month=6'
curl -sS 'http://127.0.0.1:8080/api/actual-expenses?transactionType=INCOME'
curl -sS 'http://127.0.0.1:8080/api/expense-categories?categoryType=INCOME'
```

Expected: valid JSON, no 500s.

- [ ] **Step 6: Commit final docs or command notes**

If `AGENTS.md` needs updated commands, commit:

```bash
git add AGENTS.md
git commit -m "docs: update cashflow development notes"
```

If no docs changes are needed, skip this commit.

---

## Plan Self-Review

- Spec coverage: Data model, migration, backend validation, analytics, web UI, mobile UI, naming, budget-only constraints, and QA are all mapped to tasks.
- Completeness scan: all implementation steps are specified.
- Type consistency: use `TransactionType` Java enum with values `EXPENSE` and `INCOME`; frontend uses the same string values.
- Scope check: the plan intentionally does not rename all backend `Expense` classes or create income budgets.
