# Budget Execution Analysis Design

## Background

The app already has three related expense capabilities:

- `fixed_expenses`: planned expenses by year, period, month range, and category.
- `actual_expenses`: official actual expense records by date, category, and amount.
- Bill import and OCR flows: ways to create actual expense records after preview and confirmation.

The current expense analysis page mainly explains planned expenses. The next feature upgrades it into a budget execution analysis page that compares planned expense budgets with actual spending.

## Goal

Upgrade `我的支出 > 支出分析` into `预算执行分析`.

The first release should answer four questions:

- Am I over budget this year?
- Am I over budget in the selected month?
- Which categories are over budget or close to budget?
- Which actual spending happened without any planned budget?

## Non-goals

- Do not add a new left-side menu item.
- Do not add an independent budget management table.
- Do not add income, cash-flow forecasting, approval, or budget target workflows in this release.
- Do not count raw imported bill rows until they become official `actual_expenses`.
- Do not change the existing bill import confirmation model.

## Product Decisions

### Budget Source

The budget source is the existing `fixed_expenses` data.

There is no separate budget table in the first release. Planned expenses are treated as the budget because they already represent recurring or yearly expected spending.

### Actual Source

The actual source is `actual_expenses`.

Only confirmed actual expense records are included. Import previews, skipped raw transactions, duplicates, and unconfirmed raw transactions are not counted.

### Time Scope

The page supports both yearly and monthly comparison.

- The selected year drives yearly summary, monthly trend, and category annual execution.
- The selected month drives the current-month reminder cards and optional monthly detail view.

### Budget-less Actual Spending

If a category has actual spending but no planned budget, it is shown as `未预算支出` and counted as over-budget pressure.

This keeps temporary or unexpected spending visible instead of hiding it inside normal totals.

## Page Structure

The existing `支出分析` page is upgraded instead of adding a new menu item.

### Filters

Top filters:

- Year selector.
- Month selector.
- Category level selector: `按大类` or `按小类`.

The year selector controls the whole report. The month selector controls current-month reminder cards and monthly drill-down context.

### Yearly Execution Summary

Top metric cards:

- 年度预算: total planned budget for the selected year.
- 年度实际: actual expenses in the selected year.
- 年度差额: yearly budget minus yearly actual. A negative value means over budget.
- 年度执行率: yearly actual divided by yearly budget.

### Current Month Reminder

Second metric row:

- 当月预算.
- 当月实际.
- 当月差额.
- 未预算支出金额.

This section should be visually direct. Over-budget or unbudgeted values should be easy to notice.

### Monthly Trend

Show all 12 months for the selected year:

- Monthly budget.
- Monthly actual spending.
- Monthly difference.

The chart can be a line chart or a mixed bar/line chart, depending on the existing chart component constraints.

### Category Execution Table

The main table compares budget and actual spending by category.

Columns:

- 分类.
- 年度预算.
- 年度实际.
- 年度差额.
- 执行率.
- 状态.

Supported statuses:

- 正常.
- 接近预算.
- 超支.
- 未预算.
- 未发生.

### Unbudgeted Spending List

Show categories where actual spending exists but budget is zero.

Fields:

- 分类.
- 实际金额.
- 笔数.
- 最近一笔日期.

This list helps the user decide whether a category should be added to the expense plan later.

## Calculation Rules

### Monthly Budget

Budget comes from `fixed_expenses`.

For each selected year and month:

- `MONTHLY` expense: count it when `start_month <= month <= end_month`.
- `YEARLY` expense: spread evenly across 12 months for monthly comparison.

Monthly budget is the sum of all effective monthly amounts for that month.

### Yearly Budget

Yearly budget is the sum of all 12 monthly budget values.

This keeps the annual result aligned with the monthly trend and respects month ranges.

### Monthly Actual

Monthly actual comes from `actual_expenses`.

Count records where:

- `expense_date` is inside the selected year and month.
- `user_id` belongs to the current user.

### Yearly Actual

Yearly actual is the sum of `actual_expenses` records where `expense_date` is inside the selected year.

### Category Matching

Budget is grouped by `fixed_expenses.category_id`.

Actual spending is grouped by `actual_expenses.category_id`.

When `按大类` is selected:

- Subcategory amounts roll up to the parent category.
- Categories without a parent can act as their own parent-level bucket.

When `按小类` is selected:

- Amounts stay on the direct category.

### Difference

Difference equals:

```text
budgetAmount - actualAmount
```

A negative value means over budget.

### Execution Rate

When budget is greater than zero:

```text
actualAmount / budgetAmount
```

When budget is zero and actual is greater than zero:

- Status is `未预算`.
- Execution rate displays `-`.

When budget and actual are both zero:

- The category is omitted from the main table.

### Status Rules

Status is derived in this order:

1. `未预算`: budget is 0 and actual is greater than 0.
2. `未发生`: budget is greater than 0 and actual is 0.
3. `超支`: actual is greater than budget.
4. `接近预算`: actual divided by budget is greater than or equal to 80%.
5. `正常`: actual divided by budget is below 80%.

## Backend API Design

Reuse the existing `/api/expense-analytics` namespace.

Recommended first-release endpoints:

### `GET /api/expense-analytics/execution-summary`

Query params:

- `year`: required.
- `month`: optional, default current month when omitted.
- `level`: `PARENT` or `SUB`, default `PARENT`.

Returns:

- yearly budget, actual, difference, execution rate.
- selected-month budget, actual, difference, unbudgeted amount.
- category execution rows.
- unbudgeted category rows.

### `GET /api/expense-analytics/execution-monthly-trend`

Query params:

- `year`: required.
- `level`: `PARENT` or `SUB`, default `PARENT`.

Returns 12 rows:

- month.
- budget amount.
- actual amount.
- difference amount.

### Compatibility

Keep existing planned-expense endpoints available:

- `/api/expense-analytics/summary`
- `/api/expense-analytics/by-category`
- `/api/expense-analytics/yearly-trend`
- `/api/expense-analytics/monthly-trend`

The frontend can migrate `支出分析` to the new execution endpoints without breaking older callers.

## Frontend Design

Update `ExpenseStats.vue` to display execution summary cards instead of planned-only cards.

Update `ExpenseReport.vue` or introduce a small sibling component for:

- Monthly budget vs actual trend.
- Category execution table.
- Unbudgeted spending list.

Update `App.vue` expense analysis state to load:

- execution summary.
- execution monthly trend.

The current `expenseYear`, `expenseReportLevel`, and expense category data can be reused.

## Error Handling

- Invalid year returns a validation error.
- Invalid month returns a validation error.
- Invalid category level falls back to `PARENT` or returns a validation error, matching existing API style.
- If no budget and no actual spending exist for the selected year, return zero totals and empty rows.
- If actual spending exists without budget, return normal totals plus `未预算` rows instead of treating it as an API error.

## Testing And Acceptance

Acceptance checks:

- A monthly planned expense only contributes to months inside its start/end month range.
- A yearly planned expense contributes one twelfth of its amount to each month.
- Yearly budget equals the sum of the 12 monthly budgets.
- Actual spending is counted by `expense_date`.
- Confirmed bill-import expenses are counted after they become `actual_expenses`.
- Raw imported rows that are duplicate, skipped, or unconfirmed are not counted.
- A category with actual spending and zero budget is marked `未预算`.
- A category over budget is marked `超支`.
- A category at or above 80% usage but not over budget is marked `接近预算`.
- The `按大类` view rolls subcategories into parent categories.
- The `按小类` view shows direct categories.
- The page keeps the existing `我的支出 > 支出分析` menu location.

## Implementation Boundary

This is an analytics upgrade. It should avoid broad navigation changes, new budget CRUD, or income forecasting.

The implementation should follow the existing Spring Boot, MyBatis, Vue 3, Ant Design Vue, and local fallback Node API patterns already used by the expense module.
