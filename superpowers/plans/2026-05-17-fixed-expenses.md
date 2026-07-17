# Fixed Expenses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent “我的支出” module for fixed monthly/yearly expense budgets with custom categories, preset lucide icons, CRUD screens, and summary/category analytics.

**Architecture:** Add two independent backend resources, `expense_categories` and `fixed_expenses`, using the existing Spring Boot + MyBatis XML pattern. Add frontend API clients and Vue components, then wire them into `App.vue` as a new sidebar group beside “我的资产”.

**Tech Stack:** Java 17, Spring Boot 3, MyBatis XML, MySQL 8, Vue 3 `<script setup>`, Ant Design Vue, ECharts, lucide-vue-next, Vite.

---

## File Map

- Modify: `database/schema.sql` - add `expense_categories` and `fixed_expenses` DDL plus starter categories.
- Create: `backend/src/main/java/com/example/assetmanager/domain/ExpensePeriod.java` - enum for `MONTHLY` and `YEARLY`.
- Create: `backend/src/main/java/com/example/assetmanager/domain/ExpenseCategory.java` - category domain object.
- Create: `backend/src/main/java/com/example/assetmanager/domain/FixedExpense.java` - fixed expense domain object.
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryRequest.java` - validated category create/update payload.
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryView.java` - category response with `itemCount`.
- Create: `backend/src/main/java/com/example/assetmanager/dto/FixedExpenseRequest.java` - validated expense create/update payload.
- Create: `backend/src/main/java/com/example/assetmanager/dto/FixedExpenseView.java` - expense response with category name/icon and calculated monthly/yearly amounts.
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseSummaryResponse.java` - summary cards response.
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryStats.java` - category analytics response.
- Create: `backend/src/main/java/com/example/assetmanager/mapper/ExpenseCategoryMapper.java` - MyBatis mapper interface.
- Create: `backend/src/main/java/com/example/assetmanager/mapper/FixedExpenseMapper.java` - MyBatis mapper interface.
- Create: `backend/src/main/resources/mapper/ExpenseCategoryMapper.xml` - category SQL.
- Create: `backend/src/main/resources/mapper/FixedExpenseMapper.xml` - fixed expense SQL and analytics SQL.
- Create: `backend/src/main/java/com/example/assetmanager/service/ExpenseCategoryService.java` - category business rules.
- Create: `backend/src/main/java/com/example/assetmanager/service/FixedExpenseService.java` - expense CRUD and analytics logic.
- Create: `backend/src/main/java/com/example/assetmanager/controller/ExpenseCategoryController.java` - category REST endpoints.
- Create: `backend/src/main/java/com/example/assetmanager/controller/FixedExpenseController.java` - fixed expense REST endpoints.
- Create: `backend/src/main/java/com/example/assetmanager/controller/ExpenseAnalyticsController.java` - analytics REST endpoints.
- Create: `backend/src/test/java/com/example/assetmanager/service/FixedExpenseServiceTest.java` - service-level calculation and validation tests with fake mappers.
- Modify: `frontend/src/api/client.js` - add `expenseCategoryApi`, `fixedExpenseApi`, and `expenseAnalyticsApi`.
- Create: `frontend/src/components/ExpenseIconPicker.vue` - preset lucide icon picker.
- Create: `frontend/src/components/ExpenseCategoryManager.vue` - category CRUD table/form.
- Create: `frontend/src/components/FixedExpenseManager.vue` - fixed expense CRUD table/form.
- Create: `frontend/src/components/ExpenseStats.vue` - summary cards, pie chart, category stats table.
- Modify: `frontend/src/App.vue` - add “我的支出” sidebar group, state, loading functions, handlers, and views.

## Task 1: Database Schema

**Files:**
- Modify: `database/schema.sql`

- [ ] **Step 1: Add DDL after `investment_types` and before `monthly_snapshots`**

Add this SQL. Keep existing tables and sample asset data intact.

```sql
drop table if exists fixed_expenses;
drop table if exists expense_categories;

create table expense_categories (
  id bigint primary key auto_increment,
  name varchar(100) not null unique,
  icon varchar(80) not null default 'CircleDollarSign',
  remark varchar(500),
  created_by varchar(80) not null default 'system',
  updated_by varchar(80) not null default 'system',
  created_at datetime not null default current_timestamp,
  updated_at datetime not null default current_timestamp on update current_timestamp
) engine=InnoDB default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table fixed_expenses (
  id bigint primary key auto_increment,
  name varchar(100) not null,
  category_id bigint not null,
  amount decimal(18, 2) not null,
  period enum('MONTHLY', 'YEARLY') not null,
  remark varchar(500),
  created_by varchar(80) not null default 'system',
  updated_by varchar(80) not null default 'system',
  created_at datetime not null default current_timestamp,
  updated_at datetime not null default current_timestamp on update current_timestamp,
  index idx_fixed_expenses_category (category_id),
  index idx_fixed_expenses_period (period),
  constraint fk_fixed_expense_category
    foreign key (category_id) references expense_categories(id)
) engine=InnoDB default charset=utf8mb4 collate=utf8mb4_unicode_ci;

insert into expense_categories (name, icon, remark)
values
  ('保险类', 'Shield', '保险、车险等固定支出'),
  ('日常类', 'ShoppingCart', '日常生活固定支出'),
  ('婴儿类', 'Baby', '婴儿用品、育儿相关固定支出');
```

- [ ] **Step 2: Validate SQL ordering**

Run:

```powershell
Select-String -Path database\schema.sql -Pattern "drop table if exists fixed_expenses|create table expense_categories|create table fixed_expenses|insert into expense_categories"
```

Expected: all four patterns appear before `create table monthly_snapshots`.

- [ ] **Step 3: Commit schema**

```bash
git add database/schema.sql
git commit -m "feat: add fixed expense schema"
```

## Task 2: Backend Domain And DTOs

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/domain/ExpensePeriod.java`
- Create: `backend/src/main/java/com/example/assetmanager/domain/ExpenseCategory.java`
- Create: `backend/src/main/java/com/example/assetmanager/domain/FixedExpense.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryRequest.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryView.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/FixedExpenseRequest.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/FixedExpenseView.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseSummaryResponse.java`
- Create: `backend/src/main/java/com/example/assetmanager/dto/ExpenseCategoryStats.java`

- [ ] **Step 1: Create `ExpensePeriod`**

```java
package com.example.assetmanager.domain;

public enum ExpensePeriod {
    MONTHLY,
    YEARLY
}
```

- [ ] **Step 2: Create domain objects**

Use private fields with getters and setters, matching the existing domain style. `ExpenseCategory` fields:

```java
private Long id;
private String name;
private String icon;
private String remark;
private String createdBy;
private String updatedBy;
private LocalDateTime createdAt;
private LocalDateTime updatedAt;
```

`FixedExpense` fields:

```java
private Long id;
private String name;
private Long categoryId;
private BigDecimal amount;
private ExpensePeriod period;
private String remark;
private String createdBy;
private String updatedBy;
private LocalDateTime createdAt;
private LocalDateTime updatedAt;
```

- [ ] **Step 3: Create validated request DTOs**

`ExpenseCategoryRequest` fields and annotations:

```java
@NotBlank(message = "分类名称不能为空")
private String name;

@NotBlank(message = "请选择分类图标")
private String icon;

private String remark;
```

`FixedExpenseRequest` fields and annotations:

```java
@NotBlank(message = "支出名称不能为空")
private String name;

@NotNull(message = "请选择支出分类")
private Long categoryId;

@NotNull(message = "金额不能为空")
@DecimalMin(value = "0.01", message = "金额必须大于 0")
private BigDecimal amount;

@NotNull(message = "请选择支出周期")
private ExpensePeriod period;

private String remark;
```

- [ ] **Step 4: Create response DTOs**

`ExpenseCategoryView` fields:

```java
private Long id;
private String name;
private String icon;
private String remark;
private String createdBy;
private String updatedBy;
private LocalDateTime createdAt;
private LocalDateTime updatedAt;
private Integer itemCount;
```

`FixedExpenseView` fields:

```java
private Long id;
private String name;
private Long categoryId;
private String categoryName;
private String categoryIcon;
private BigDecimal amount;
private ExpensePeriod period;
private BigDecimal monthlyAmount;
private BigDecimal yearlyAmount;
private String remark;
private String createdBy;
private String updatedBy;
private LocalDateTime createdAt;
private LocalDateTime updatedAt;
```

`ExpenseSummaryResponse` fields:

```java
private BigDecimal monthlyTotal;
private BigDecimal yearlyTotal;
```

`ExpenseCategoryStats` fields:

```java
private Long categoryId;
private String categoryName;
private String icon;
private BigDecimal monthlyAmount;
private BigDecimal yearlyAmount;
private Integer itemCount;
```

- [ ] **Step 5: Compile DTO/domain layer**

Run:

```powershell
cd backend
mvn -q -DskipTests compile
```

Expected: compilation succeeds.

- [ ] **Step 6: Commit domain and DTOs**

```bash
git add backend/src/main/java/com/example/assetmanager/domain backend/src/main/java/com/example/assetmanager/dto
git commit -m "feat: add fixed expense models"
```

## Task 3: Backend Mappers And SQL

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/mapper/ExpenseCategoryMapper.java`
- Create: `backend/src/main/java/com/example/assetmanager/mapper/FixedExpenseMapper.java`
- Create: `backend/src/main/resources/mapper/ExpenseCategoryMapper.xml`
- Create: `backend/src/main/resources/mapper/FixedExpenseMapper.xml`

- [ ] **Step 1: Create mapper interfaces**

`ExpenseCategoryMapper`:

```java
package com.example.assetmanager.mapper;

import com.example.assetmanager.domain.ExpenseCategory;
import com.example.assetmanager.dto.ExpenseCategoryView;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface ExpenseCategoryMapper {
    List<ExpenseCategoryView> findAll();
    ExpenseCategory findById(@Param("id") Long id);
    ExpenseCategory findByName(@Param("name") String name);
    void insert(ExpenseCategory category);
    void update(ExpenseCategory category);
    int countExpenses(@Param("id") Long id);
    void delete(@Param("id") Long id);
}
```

`FixedExpenseMapper`:

```java
package com.example.assetmanager.mapper;

import com.example.assetmanager.domain.FixedExpense;
import com.example.assetmanager.dto.ExpenseCategoryStats;
import com.example.assetmanager.dto.FixedExpenseView;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface FixedExpenseMapper {
    List<FixedExpenseView> findAll(@Param("categoryId") Long categoryId, @Param("period") String period);
    FixedExpense findById(@Param("id") Long id);
    void insert(FixedExpense expense);
    void update(FixedExpense expense);
    void delete(@Param("id") Long id);
    List<ExpenseCategoryStats> statsByCategory();
}
```

- [ ] **Step 2: Create `ExpenseCategoryMapper.xml`**

Include result maps for `ExpenseCategory` and `ExpenseCategoryView`. The list query must left join `fixed_expenses` and return `item_count`.

```xml
<select id="findAll" resultMap="ExpenseCategoryViewResultMap">
    select c.*, count(e.id) as item_count
    from expense_categories c
    left join fixed_expenses e on e.category_id = c.id
    group by c.id
    order by c.updated_at desc, c.id desc
</select>
```

The delete guard lives in service, but the mapper must expose:

```xml
<select id="countExpenses" resultType="int">
    select count(*) from fixed_expenses where category_id = #{id}
</select>
```

- [ ] **Step 3: Create `FixedExpenseMapper.xml`**

The `findAll` query must return calculated values:

```xml
<select id="findAll" resultMap="FixedExpenseViewResultMap">
    select e.*,
           c.name as category_name,
           c.icon as category_icon,
           case when e.period = 'MONTHLY' then e.amount else 0 end as monthly_amount,
           case when e.period = 'MONTHLY' then e.amount * 12 else e.amount end as yearly_amount
    from fixed_expenses e
    join expense_categories c on c.id = e.category_id
    where (#{categoryId} is null or e.category_id = #{categoryId})
      and (#{period} is null or e.period = #{period})
    order by c.updated_at desc, c.id desc, e.updated_at desc, e.id desc
</select>
```

The category stats query must group by category:

```xml
<select id="statsByCategory" resultMap="ExpenseCategoryStatsResultMap">
    select c.id as category_id,
           c.name as category_name,
           c.icon,
           coalesce(sum(case when e.period = 'MONTHLY' then e.amount else 0 end), 0) as monthly_amount,
           coalesce(sum(case when e.period = 'MONTHLY' then e.amount * 12 else e.amount end), 0) as yearly_amount,
           count(e.id) as item_count
    from expense_categories c
    left join fixed_expenses e on e.category_id = c.id
    group by c.id
    order by c.updated_at desc, c.id desc
</select>
```

- [ ] **Step 4: Compile mapper layer**

Run:

```powershell
cd backend
mvn -q -DskipTests compile
```

Expected: MyBatis XML loads during compile resources phase without syntax errors.

- [ ] **Step 5: Commit mappers**

```bash
git add backend/src/main/java/com/example/assetmanager/mapper backend/src/main/resources/mapper
git commit -m "feat: add fixed expense mappers"
```

## Task 4: Backend Services, Controllers, And Tests

**Files:**
- Create: `backend/src/main/java/com/example/assetmanager/service/ExpenseCategoryService.java`
- Create: `backend/src/main/java/com/example/assetmanager/service/FixedExpenseService.java`
- Create: `backend/src/main/java/com/example/assetmanager/controller/ExpenseCategoryController.java`
- Create: `backend/src/main/java/com/example/assetmanager/controller/FixedExpenseController.java`
- Create: `backend/src/main/java/com/example/assetmanager/controller/ExpenseAnalyticsController.java`
- Create: `backend/src/test/java/com/example/assetmanager/service/FixedExpenseServiceTest.java`

- [ ] **Step 1: Write service tests first**

Create `FixedExpenseServiceTest` with fake mapper classes. Include these tests:

```java
@Test
void summaryCalculatesMonthlyAndYearlyTotals() {
    FakeFixedExpenseMapper mapper = new FakeFixedExpenseMapper();
    mapper.stats = List.of(
        stats(1L, "日常类", "ShoppingCart", "100.00", "1200.00", 1),
        stats(2L, "保险类", "Shield", "0.00", "3600.00", 1)
    );
    FixedExpenseService service = new FixedExpenseService(mapper, new FakeExpenseCategoryMapper());

    ExpenseSummaryResponse result = service.summary();

    assertThat(result.getMonthlyTotal()).isEqualByComparingTo("100.00");
    assertThat(result.getYearlyTotal()).isEqualByComparingTo("4800.00");
}

@Test
void createRejectsMissingCategory() {
    FixedExpenseService service = new FixedExpenseService(new FakeFixedExpenseMapper(), new FakeExpenseCategoryMapper());
    FixedExpenseRequest request = request("奶粉", 99L, "300.00", ExpensePeriod.MONTHLY);

    assertThatThrownBy(() -> service.create(request))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessage("请选择支出分类");
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
cd backend
mvn -q -Dtest=FixedExpenseServiceTest test
```

Expected: FAIL because `FixedExpenseService` does not exist or lacks required methods.

- [ ] **Step 3: Implement services**

`ExpenseCategoryService` must:

- Return `expenseCategoryMapper.findAll()`.
- On create/update, trim `name`, default blank icon to `CircleDollarSign`, set `createdBy` and `updatedBy` to `system`.
- Reject duplicate names with `IllegalArgumentException("分类名称已存在")`.
- Reject deleting a used category with `IllegalArgumentException("该分类下存在支出项目，无法删除")`.

`FixedExpenseService` must:

- Validate category exists before create/update; if missing, throw `IllegalArgumentException("请选择支出分类")`.
- Set `createdBy` and `updatedBy` to `system`.
- Use `fixedExpenseMapper.findAll(categoryId, period == null ? null : period.name())`.
- Calculate `summary()` from `statsByCategory()` by summing monthly and yearly amounts.
- Return `statsByCategory()` for category analytics.

- [ ] **Step 4: Implement controllers**

`ExpenseCategoryController`:

```java
@RestController
@RequestMapping("/api/expense-categories")
public class ExpenseCategoryController {
    @GetMapping
    public List<ExpenseCategoryView> list() { return expenseCategoryService.list(); }

    @PostMapping
    public ExpenseCategory create(@Valid @RequestBody ExpenseCategoryRequest request) { return expenseCategoryService.create(request); }

    @PutMapping("/{id}")
    public ExpenseCategory update(@PathVariable Long id, @Valid @RequestBody ExpenseCategoryRequest request) { return expenseCategoryService.update(id, request); }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) { expenseCategoryService.delete(id); }
}
```

`FixedExpenseController`:

```java
@RestController
@RequestMapping("/api/fixed-expenses")
public class FixedExpenseController {
    @GetMapping
    public List<FixedExpenseView> list(@RequestParam(required = false) Long categoryId,
                                       @RequestParam(required = false) ExpensePeriod period) {
        return fixedExpenseService.list(categoryId, period);
    }
}
```

Add POST, PUT, DELETE methods matching the existing controller style.

`ExpenseAnalyticsController`:

```java
@RestController
@RequestMapping("/api/expense-analytics")
public class ExpenseAnalyticsController {
    @GetMapping("/summary")
    public ExpenseSummaryResponse summary() { return fixedExpenseService.summary(); }

    @GetMapping("/by-category")
    public List<ExpenseCategoryStats> byCategory() { return fixedExpenseService.statsByCategory(); }
}
```

- [ ] **Step 5: Run backend tests**

Run:

```powershell
cd backend
mvn test
```

Expected: PASS.

- [ ] **Step 6: Commit backend services and controllers**

```bash
git add backend/src/main/java/com/example/assetmanager/service backend/src/main/java/com/example/assetmanager/controller backend/src/test/java/com/example/assetmanager/service/FixedExpenseServiceTest.java
git commit -m "feat: add fixed expense APIs"
```

## Task 5: Frontend API And Icon Picker

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/components/ExpenseIconPicker.vue`

- [ ] **Step 1: Add API clients**

Append these exports to `frontend/src/api/client.js`:

```js
export const expenseCategoryApi = {
  list: () => api.get('/expense-categories').then((res) => res.data),
  create: (payload) => api.post('/expense-categories', payload).then((res) => res.data),
  update: (id, payload) => api.put(`/expense-categories/${id}`, payload).then((res) => res.data),
  remove: (id) => api.delete(`/expense-categories/${id}`).then((res) => res.data)
}

export const fixedExpenseApi = {
  list: (params = {}) => api.get('/fixed-expenses', { params }).then((res) => res.data),
  create: (payload) => api.post('/fixed-expenses', payload).then((res) => res.data),
  update: (id, payload) => api.put(`/fixed-expenses/${id}`, payload).then((res) => res.data),
  remove: (id) => api.delete(`/fixed-expenses/${id}`).then((res) => res.data)
}

export const expenseAnalyticsApi = {
  summary: () => api.get('/expense-analytics/summary').then((res) => res.data),
  byCategory: () => api.get('/expense-analytics/by-category').then((res) => res.data)
}
```

- [ ] **Step 2: Create icon picker**

Use lucide components imported by name. The component accepts `modelValue`, emits `update:modelValue`, and renders a compact grid of these names:

```js
const iconOptions = [
  'Shield', 'ShoppingCart', 'Baby', 'Home', 'Wifi',
  'Utensils', 'Car', 'HeartPulse', 'GraduationCap', 'Laptop',
  'Plane', 'Dumbbell', 'Gift', 'CircleDollarSign'
]
```

Use a fallback:

```js
const selectedIcon = computed(() => icons[props.modelValue] || icons.CircleDollarSign)
```

- [ ] **Step 3: Build frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: Vite build succeeds and lucide imports resolve.

- [ ] **Step 4: Commit API and icon picker**

```bash
git add frontend/src/api/client.js frontend/src/components/ExpenseIconPicker.vue
git commit -m "feat: add expense frontend API client"
```

## Task 6: Frontend Expense Pages

**Files:**
- Create: `frontend/src/components/ExpenseCategoryManager.vue`
- Create: `frontend/src/components/FixedExpenseManager.vue`
- Create: `frontend/src/components/ExpenseStats.vue`

- [ ] **Step 1: Create `ExpenseCategoryManager.vue`**

Props:

```js
const props = defineProps({
  categories: { type: Array, default: () => [] }
})
```

Emits:

```js
const emit = defineEmits(['save', 'remove'])
```

Form fields: `name`, `icon`, `remark`. The delete button emits `remove(record)`. The save event payload shape:

```js
emit('save', {
  id: editingId.value,
  payload: {
    name: form.value.name.trim(),
    icon: form.value.icon || 'CircleDollarSign',
    remark: form.value.remark || ''
  },
  done: (success) => {
    if (success) resetForm()
  }
})
```

- [ ] **Step 2: Create `FixedExpenseManager.vue`**

Props:

```js
const props = defineProps({
  expenses: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] }
})
```

Emits:

```js
const emit = defineEmits(['save', 'remove', 'filter'])
```

Render columns: name, category name with icon, amount, period label, monthlyAmount, yearlyAmount, remark, actions. Use labels:

```js
const periodLabel = (period) => ({ MONTHLY: '每月', YEARLY: '每年' }[period] || period)
```

Save payload:

```js
emit('save', {
  id: editingId.value,
  payload: {
    name: form.value.name.trim(),
    categoryId: form.value.categoryId,
    amount: Number(form.value.amount),
    period: form.value.period,
    remark: form.value.remark || ''
  },
  done: (success) => {
    if (success) resetForm()
  }
})
```

- [ ] **Step 3: Create `ExpenseStats.vue`**

Props:

```js
const props = defineProps({
  summary: { type: Object, default: () => ({ monthlyTotal: 0, yearlyTotal: 0 }) },
  categoryStats: { type: Array, default: () => [] }
})
```

Render two cards only: `每月固定支出` and `每年固定支出`. Use existing `PieChart` for category yearly amount:

```js
const piePoints = computed(() =>
  props.categoryStats
    .filter((item) => Number(item.yearlyAmount || 0) > 0)
    .map((item) => ({ name: item.categoryName, value: Number(item.yearlyAmount || 0) }))
)
```

Render table columns: icon, categoryName, monthlyAmount, yearlyAmount, itemCount.

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 5: Commit expense components**

```bash
git add frontend/src/components/ExpenseCategoryManager.vue frontend/src/components/FixedExpenseManager.vue frontend/src/components/ExpenseStats.vue
git commit -m "feat: add expense management components"
```

## Task 7: Wire Expense Module Into `App.vue`

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add imports**

Extend API import:

```js
import {
  accountApi,
  accountNameApi,
  analyticsApi,
  expenseAnalyticsApi,
  expenseCategoryApi,
  fixedExpenseApi,
  investmentTypeApi,
  snapshotApi
} from './api/client'
```

Add lucide icons:

```js
import { ReceiptText, ChartPie, ListChecks, Shapes } from 'lucide-vue-next'
```

Add components:

```js
import ExpenseCategoryManager from './components/ExpenseCategoryManager.vue'
import ExpenseStats from './components/ExpenseStats.vue'
import FixedExpenseManager from './components/FixedExpenseManager.vue'
```

- [ ] **Step 2: Add state and computed values**

```js
const expenseManageOpen = ref(false)
const expenseCategories = ref([])
const fixedExpenses = ref([])
const expenseSummary = ref({ monthlyTotal: 0, yearlyTotal: 0 })
const expenseCategoryStats = ref([])
const expenseFilters = ref({ categoryId: '', period: '' })

const isExpenseManageActive = computed(() =>
  ['expenseStats', 'fixedExpenses', 'expenseCategories'].includes(activeView.value)
)
```

- [ ] **Step 3: Add loader and handler functions**

```js
const loadExpenseCategories = async () => {
  expenseCategories.value = await expenseCategoryApi.list()
}

const loadFixedExpenses = async () => {
  fixedExpenses.value = await fixedExpenseApi.list({
    categoryId: expenseFilters.value.categoryId || undefined,
    period: expenseFilters.value.period || undefined
  })
}

const loadExpenseAnalytics = async () => {
  const [summaryData, categoryData] = await Promise.all([
    expenseAnalyticsApi.summary(),
    expenseAnalyticsApi.byCategory()
  ])
  expenseSummary.value = summaryData
  expenseCategoryStats.value = categoryData
}
```

Add `openExpenseStats`, `openFixedExpenses`, and `openExpenseCategories`, each setting `activeView`, opening the group, and loading the required data.

- [ ] **Step 4: Add sidebar group**

Place after “我的资产”:

```vue
<button class="parent-nav" :class="{ active: isExpenseManageActive }" @click="expenseManageOpen = !expenseManageOpen">
  <ReceiptText :size="18" />
  <span>我的支出</span>
  <ChevronDown :size="16" :class="{ rotated: expenseManageOpen }" />
</button>
<div v-if="expenseManageOpen" class="sub-nav-wrap">
  <button class="sub-nav" :class="{ active: activeView === 'expenseStats' }" @click="openExpenseStats">
    <ChartPie :size="16" />
    <span>支出统计</span>
  </button>
  <button class="sub-nav" :class="{ active: activeView === 'fixedExpenses' }" @click="openFixedExpenses">
    <ListChecks :size="16" />
    <span>支出项目</span>
  </button>
  <button class="sub-nav" :class="{ active: activeView === 'expenseCategories' }" @click="openExpenseCategories">
    <Shapes :size="16" />
    <span>支出分类</span>
  </button>
</div>
```

- [ ] **Step 5: Add view sections**

Add three `v-else-if` sections for `expenseStats`, `fixedExpenses`, and `expenseCategories`, using the three new components and passing the relevant props/events.

- [ ] **Step 6: Extend `onMounted`**

Load expense data without blocking existing asset data:

```js
await Promise.all([
  loadAccounts(),
  loadAccountNames(),
  loadInvestmentTypes(),
  loadSnapshotMonths(),
  loadExpenseCategories()
])
await Promise.all([loadMonthData(), loadAccountMonthData(), loadExpenseAnalytics(), loadFixedExpenses()])
```

- [ ] **Step 7: Build frontend**

Run:

```powershell
cd frontend
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 8: Commit App wiring**

```bash
git add frontend/src/App.vue
git commit -m "feat: wire fixed expenses into app"
```

## Task 8: End-To-End Verification

**Files:**
- No planned code edits unless verification reveals a defect.

- [ ] **Step 1: Run backend tests**

```powershell
cd backend
mvn test
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

```powershell
cd frontend
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 3: Run full git diff review**

```powershell
git status --short
git log --oneline -8
git diff HEAD~7..HEAD --stat
```

Expected: changes are limited to fixed expense schema, backend module, frontend module, and docs.

- [ ] **Step 4: Manual smoke test with running app**

Start backend and frontend:

```powershell
cd backend
mvn spring-boot:run
```

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Verify:

- Sidebar shows “我的支出”.
- “支出分类” can create a category with icon.
- Duplicate category name shows “分类名称已存在”.
- “支出项目” can create monthly and yearly items.
- Amount `0` is rejected with “金额必须大于 0”.
- “支出统计” shows monthly total as monthly item sum.
- “支出统计” shows yearly total as monthly item sum times 12 plus yearly item sum.
- Deleting a category used by an item shows “该分类下存在支出项目，无法删除”.

- [ ] **Step 5: Final commit if smoke-test fixes were needed**

If fixes were made during verification:

```bash
git add <changed-files>
git commit -m "fix: polish fixed expense flow"
```

If no fixes were needed, do not create an empty commit.

## Self-Review Notes

- Spec coverage: the plan covers custom categories, preset icons, monthly/yearly periods, no payment platform, no active state, audit user fields defaulting to `system`, summary cards, category stats, deletion guard, and independent module wiring.
- Placeholder scan: no unresolved markers or open-ended validation steps remain.
- Type consistency: backend uses `ExpensePeriod`, `ExpenseCategory`, `FixedExpense`, `ExpenseCategoryView`, `FixedExpenseView`, `ExpenseSummaryResponse`, and `ExpenseCategoryStats`; frontend uses `monthlyTotal`, `yearlyTotal`, `monthlyAmount`, `yearlyAmount`, `categoryName`, and `icon` consistently.
