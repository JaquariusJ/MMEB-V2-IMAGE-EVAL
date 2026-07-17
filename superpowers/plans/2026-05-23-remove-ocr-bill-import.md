# Remove OCR + Bill Import Implementation Plan

> **For agentic workers:** This is a cleanup/deletion task. No TDD needed — follow each step exactly, delete what's specified, verify builds pass at the end.

**Goal:** Remove OCR (PaddleOCR model-service), WeChat/Alipay bill import features, and all related code/files from the project.

**Architecture:** Remove standalone model-service entirely. Strip bill-import and OCR code from the shared ActualExpenseService/Controller/Component. Clean database schema. Rebuild 3-container stack (mysql, backend, frontend).

**Tech Stack:** Java 17 / Spring Boot, Vue 3, Docker Compose, MySQL

---

## Task 1: Delete standalone files and directories

**Files:**
- Delete: `model-service/` (entire directory — ocr_engine.py, main.py, requirements.txt, Dockerfile)
- Delete: `dev-tools/ocr_service.py`
- Delete: `dev-tools/paddle_ocr.py`
- Delete: `backend/src/test/java/com/example/assetmanager/service/ActualExpenseImportServiceTest.java`
- Delete: `docs/superpowers/specs/2026-05-22-bill-import-design.md`

- [ ] **Step 1: Delete model-service directory**

```bash
rm -rf model-service/
```

- [ ] **Step 2: Delete OCR dev scripts**

```bash
rm -f dev-tools/ocr_service.py dev-tools/paddle_ocr.py
```

- [ ] **Step 3: Delete bill import test and design doc**

```bash
rm -f backend/src/test/java/com/example/assetmanager/service/ActualExpenseImportServiceTest.java
rm -f docs/superpowers/specs/2026-05-22-bill-import-design.md
```

---

## Task 2: Clean docker-compose.yml, .env.example, deploy.py

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `scripts/deploy.py`

- [ ] **Step 1: Remove model-service from docker-compose.yml**

Delete the entire `model-service:` service block (lines 27-46). Remove `OCR_SERVICE_URL` env var and `model-service` dependency from the `backend` service. The result:

```yaml
services:
  mysql:
    image: docker.m.daocloud.io/library/mysql:8.0
    container_name: asset-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-asset_manager}
      TZ: Asia/Shanghai
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-time-zone=+08:00
    ports:
      - "${MYSQL_PORT:-3578}:3306"
    volumes:
      - asset_mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -uroot -p$${MYSQL_ROOT_PASSWORD} --silent"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s
    networks:
      - asset-manager-net

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: asset-manager-backend
    restart: unless-stopped
    environment:
      MYSQL_URL: ${MYSQL_URL:-jdbc:mysql://mysql:3306/asset_manager?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true}
      MYSQL_USERNAME: ${MYSQL_USERNAME:-root}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}
      AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:-manage-me-local-secret-change-me}
      AUTH_DEV_MODE: ${AUTH_DEV_MODE:-false}
      TZ: Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - asset-manager-net

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: asset-manager-frontend
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "80:80"
    networks:
      - asset-manager-net

volumes:
  asset_mysql_data:
    name: asset_mysql_data
    external: true

networks:
  asset-manager-net:
    driver: bridge
```

- [ ] **Step 2: Clean .env.example**

Remove `OCR_SERVICE_URL` line. Result:

```
MYSQL_URL=jdbc:mysql://mysql:3306/asset_manager?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_USERNAME=root
MYSQL_PASSWORD=replace-with-your-password
MYSQL_ROOT_PASSWORD=replace-with-your-password
MYSQL_DATABASE=asset_manager
MYSQL_PORT=3578
AUTH_JWT_SECRET=change-me
AUTH_DEV_MODE=false
```

- [ ] **Step 3: Clean deploy.py — remove model-service from archive and .env**

In `create_release_archive()`, delete the line:
```python
add_path(tar, ROOT / "model-service", "model-service")
```

In `write_env_file()`, delete the line:
```python
"OCR_SERVICE_URL=http://model-service:8099",
```

---

## Task 3: Clean backend Java — ActualExpenseService

**Files:**
- Modify: `backend/src/main/java/com/example/assetmanager/service/ActualExpenseService.java`

- [ ] **Step 1: Rewrite ActualExpenseService.java keeping only CRUD + bulkCreate**

Remove: OCR RestClient, previewOcr(), callOcrService(), autoFillCategories(), previewBillImport(), confirmBillImport(), all bill parsing methods (parseBillFile, parseBillRows, parseWechatRow, parseAlipayRow, classifyTransactionKind, etc.), BillImportConfirmResponse, BulkCreateResponse (keep if used elsewhere — check first), ensureRawImportAvailable(), normalizePlatform().

Keep: list(), create(), update(), delete(), bulkCreate(), applyRequest(), validateCategory().

The cleaned file should be ~100 lines:

```java
package com.example.assetmanager.service;

import com.example.assetmanager.domain.ActualExpense;
import com.example.assetmanager.dto.ActualExpenseRequest;
import com.example.assetmanager.dto.ActualExpenseView;
import com.example.assetmanager.mapper.ActualExpenseMapper;
import com.example.assetmanager.mapper.ExpenseCategoryMapper;
import com.example.assetmanager.security.CurrentUserHolder;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

@Service
public class ActualExpenseService {

    private final ActualExpenseMapper expenseMapper;
    private final ExpenseCategoryMapper categoryMapper;

    public ActualExpenseService(ActualExpenseMapper expenseMapper, ExpenseCategoryMapper categoryMapper) {
        this.expenseMapper = expenseMapper;
        this.categoryMapper = categoryMapper;
    }

    public List<ActualExpenseView> list(String startDate, String endDate, Long categoryId) {
        Long userId = CurrentUserHolder.get().getId();
        return expenseMapper.findAll(userId, startDate, endDate, categoryId);
    }

    public ActualExpense create(ActualExpenseRequest request) {
        Long userId = CurrentUserHolder.get().getId();
        validateCategory(userId, request.getCategoryId());
        ActualExpense expense = applyRequest(userId, request);
        expenseMapper.insert(expense);
        return expenseMapper.findById(expense.getId());
    }

    public ActualExpense update(Long id, ActualExpenseRequest request) {
        Long userId = CurrentUserHolder.get().getId();
        validateCategory(userId, request.getCategoryId());
        ActualExpense expense = applyRequest(userId, request);
        expense.setId(id);
        expenseMapper.update(expense);
        return expenseMapper.findById(id);
    }

    public void delete(Long id) {
        Long userId = CurrentUserHolder.get().getId();
        expenseMapper.delete(userId, id);
    }

    public BulkCreateResponse bulkCreate(List<ActualExpenseRequest> items) {
        int created = 0;
        for (ActualExpenseRequest item : items) {
            create(item);
            created++;
        }
        return new BulkCreateResponse(created);
    }

    private void validateCategory(Long userId, Long categoryId) {
        if (categoryId == null) {
            throw new IllegalArgumentException("类别不能为空");
        }
        if (categoryMapper.findById(userId, categoryId) == null) {
            throw new IllegalArgumentException("类别不存在");
        }
    }

    private ActualExpense applyRequest(Long userId, ActualExpenseRequest request) {
        ActualExpense expense = new ActualExpense();
        expense.setUserId(userId);
        expense.setExpenseDate(request.getExpenseDate());
        expense.setCategoryId(request.getCategoryId());
        expense.setAmount(request.getAmount());
        expense.setMerchant(request.getMerchant());
        expense.setNote(request.getNote());
        expense.setSourceType(request.getSourceType());
        expense.setSourceText(request.getSourceText());
        expense.setSourceImageName(request.getSourceImageName());
        return expense;
    }

    public record BulkCreateResponse(int created) {}
}
```

---

## Task 4: Clean backend — Controller, DTOs, Domain, Mapper

**Files:**
- Modify: `backend/src/main/java/com/example/assetmanager/controller/ActualExpenseController.java`
- Delete: `backend/src/main/java/com/example/assetmanager/dto/OcrPreviewRequest.java`
- Delete: `backend/src/main/java/com/example/assetmanager/dto/OcrPreviewResponse.java`
- Delete: `backend/src/main/java/com/example/assetmanager/dto/BillImportPreviewResponse.java`
- Delete: `backend/src/main/java/com/example/assetmanager/dto/BillImportConfirmRequest.java`
- Delete: `backend/src/main/java/com/example/assetmanager/domain/RawTransaction.java`
- Delete: `backend/src/main/java/com/example/assetmanager/mapper/RawTransactionMapper.java`
- Delete: `backend/src/main/resources/mapper/RawTransactionMapper.xml`
- Modify: `backend/src/main/java/com/example/assetmanager/domain/ActualExpense.java`
- Modify: `backend/src/main/java/com/example/assetmanager/mapper/ActualExpenseMapper.java`
- Modify: `backend/src/main/resources/mapper/ActualExpenseMapper.xml`

- [ ] **Step 1: Delete dedicated OCR/bill-import DTOs, domain, and mapper files**

```bash
rm -f backend/src/main/java/com/example/assetmanager/dto/OcrPreviewRequest.java
rm -f backend/src/main/java/com/example/assetmanager/dto/OcrPreviewResponse.java
rm -f backend/src/main/java/com/example/assetmanager/dto/BillImportPreviewResponse.java
rm -f backend/src/main/java/com/example/assetmanager/dto/BillImportConfirmRequest.java
rm -f backend/src/main/java/com/example/assetmanager/domain/RawTransaction.java
rm -f backend/src/main/java/com/example/assetmanager/mapper/RawTransactionMapper.java
rm -f backend/src/main/resources/mapper/RawTransactionMapper.xml
```

- [ ] **Step 2: Clean ActualExpenseController — remove import-preview, import-confirm, ocr-preview endpoints**

Keep only: GET /, POST /, POST /bulk, PUT /{id}, DELETE /{id}.

```java
package com.example.assetmanager.controller;

import com.example.assetmanager.domain.ActualExpense;
import com.example.assetmanager.dto.ActualExpenseRequest;
import com.example.assetmanager.dto.ActualExpenseView;
import com.example.assetmanager.service.ActualExpenseService;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;
import java.util.List;

@RestController
@RequestMapping("/api/actual-expenses")
public class ActualExpenseController {

    private final ActualExpenseService service;

    public ActualExpenseController(ActualExpenseService service) {
        this.service = service;
    }

    @GetMapping
    public List<ActualExpenseView> list(
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            @RequestParam(required = false) Long categoryId) {
        return service.list(startDate, endDate, categoryId);
    }

    @PostMapping
    public ActualExpense create(@Valid @RequestBody ActualExpenseRequest request) {
        return service.create(request);
    }

    @PostMapping("/bulk")
    public ActualExpenseService.BulkCreateResponse bulkCreate(@Valid @RequestBody List<ActualExpenseRequest> items) {
        return service.bulkCreate(items);
    }

    @PutMapping("/{id}")
    public ActualExpense update(@PathVariable Long id, @Valid @RequestBody ActualExpenseRequest request) {
        return service.update(id, request);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
```

- [ ] **Step 3: Clean ActualExpense.java — remove bill-import fields**

Remove fields: sourcePlatform, externalTradeNo, externalOrderNo, importBatchNo, rawTransactionId, verifyStatus. Keep: id, userId, expenseDate, categoryId, amount, merchant, note, sourceType, sourceText, sourceImageName, createdAt, updatedAt.

```java
package com.example.assetmanager.domain;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

public class ActualExpense {
    private Long id;
    private Long userId;
    private LocalDate expenseDate;
    private Long categoryId;
    private BigDecimal amount;
    private String merchant;
    private String note;
    private String sourceType;
    private String sourceText;
    private String sourceImageName;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void getUserId(Long userId) { this.userId = userId; }
    public LocalDate getExpenseDate() { return expenseDate; }
    public void setExpenseDate(LocalDate expenseDate) { this.expenseDate = expenseDate; }
    public Long getCategoryId() { return categoryId; }
    public void setCategoryId(Long categoryId) { this.categoryId = categoryId; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public String getMerchant() { return merchant; }
    public void setMerchant(String merchant) { this.merchant = merchant; }
    public String getNote() { return note; }
    public void setNote(String note) { this.note = note; }
    public String getSourceType() { return sourceType; }
    public void setSourceType(String sourceType) { this.sourceType = sourceType; }
    public String getSourceText() { return sourceText; }
    public void setSourceText(String sourceText) { this.sourceText = sourceText; }
    public String getSourceImageName() { return sourceImageName; }
    public void setSourceImageName(String sourceImageName) { this.sourceImageName = sourceImageName; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
```

- [ ] **Step 4: Clean ActualExpenseMapper.java — remove bill-import methods**

Remove: findByPlatformAndTradeNo(), findPotentialDuplicate(), findCategoryByMerchant(). Keep: findAll(), findById(), insert(), update(), delete().

```java
package com.example.assetmanager.mapper;

import com.example.assetmanager.domain.ActualExpense;
import com.example.assetmanager.dto.ActualExpenseView;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface ActualExpenseMapper {
    List<ActualExpenseView> findAll(@Param("userId") Long userId,
                                    @Param("startDate") String startDate,
                                    @Param("endDate") String endDate,
                                    @Param("categoryId") Long categoryId);
    ActualExpense findById(@Param("id") Long id);
    void insert(ActualExpense expense);
    void update(ActualExpense expense);
    void delete(@Param("userId") Long userId, @Param("id") Long id);
}
```

- [ ] **Step 5: Clean ActualExpenseMapper.xml — remove bill-import queries and result mappings**

Remove from ActualExpenseResultMap: source_platform, external_trade_no, external_order_no, import_batch_no, raw_transaction_id, verify_status result mappings.
Remove queries: findByPlatformAndTradeNo (lines 71-78), findPotentialDuplicate (lines 80-90), findCategoryByMerchant (lines 131-142).
Remove bill-import columns from insert and update SQL.
The cleaned mapper.xml keeps: ActualExpenseResultMap (core fields only), findAll, findById, insert, update, delete.

---

## Task 5: Clean backend config

**Files:**
- Modify: `backend/src/main/resources/application.yml`
- Modify: `backend/pom.xml`

- [ ] **Step 1: Remove ocr.service.url from application.yml**

Delete lines:
```yaml
  service:
    url: ${OCR_SERVICE_URL:http://localhost:8099}
```
(Delete the entire `ocr:` section if it only contains this)

- [ ] **Step 2: Remove Apache POI dependency from pom.xml**

Delete:
```xml
<dependency>
    <groupId>org.apache.poi</groupId>
    <artifactId>poi-ooxml</artifactId>
    <version>5.3.0</version>
</dependency>
```

---

## Task 6: Clean frontend

**Files:**
- Modify: `frontend/src/components/ActualExpenseManager.vue`
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Clean ActualExpenseManager.vue — remove OCR modal, bill import modal, related buttons/scripts**

From template:
- Remove "导入账单" button (line 31 area)
- Remove entire bill import modal block (lines 107-177)
- Remove entire OCR modal block (lines 179-243)

From script:
- Remove emits: 'ocr-preview', 'bulk-save', 'import-preview', 'import-confirm'
- Remove refs: showImportModal, importPlatform, importFile, importPreview, importLoading, importSummary, importItems, showOcrModal, ocrFile, ocrDraftItems, ocrLoading, etc.
- Remove importColumns, draftColumns column definitions
- Remove sourceTag() helper (or simplify if still needed for non-import sources)
- Remove verifyTag(), kindTag() helpers (only used for bill import)
- Remove handlers: openOcrModal, handleBillFileChange, handleImageChange, doOcrPreview, submitOcr, submitBillImport, handleSelectAllImport, handleImportSelectionChange
- Remove 'bulk-save' from emits

- [ ] **Step 2: Clean client.js — remove OCR and import API functions**

From actualExpenseApi, remove: importPreview, importConfirm, ocrPreview. Keep: list, create, bulkCreate, update, remove.

- [ ] **Step 3: Clean App.vue — remove OCR/import event bindings and handlers**

From template: Remove @ocr-preview, @import-preview, @import-confirm bindings.
From script: Remove previewActualExpenseOcr, previewActualExpenseImport, confirmActualExpenseImport handler functions.

---

## Task 7: Clean database schema

**Files:**
- Modify: `database/schema.sql`
- Create: `database/migrations/011_remove_ocr_bill_import.sql`

- [ ] **Step 1: Clean schema.sql**

Remove: raw_transactions table definition (lines 139-169).
Clean actual_expenses table: remove source_platform, external_trade_no, external_order_no, import_batch_no, raw_transaction_id, verify_status columns; remove unique index on (user_id, source_platform, external_trade_no); remove FK to raw_transactions.
Update DROP TABLE statements: remove raw_transactions from the list.

- [ ] **Step 2: Create migration script for existing databases**

```sql
-- 011_remove_ocr_bill_import.sql
-- Remove bill import related tables and columns

SET @db = DATABASE();

-- Drop foreign key on actual_expenses -> raw_transactions if it exists
SET @fk_name = (
    SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'actual_expenses'
      AND REFERENCED_TABLE_NAME = 'raw_transactions' LIMIT 1
);
SET @sql = IF(@fk_name IS NOT NULL,
    CONCAT('ALTER TABLE actual_expenses DROP FOREIGN KEY ', @fk_name),
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Drop unique index on (user_id, source_platform, external_trade_no) if it exists
SET @idx_exists = (SELECT COUNT(1) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'actual_expenses'
      AND INDEX_NAME = 'uk_platform_trade_no');
SET @sql = IF(@idx_exists > 0,
    'ALTER TABLE actual_expenses DROP INDEX uk_platform_trade_no',
    'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Drop bill-import columns from actual_expenses
ALTER TABLE actual_expenses
    DROP COLUMN IF EXISTS source_platform,
    DROP COLUMN IF EXISTS external_trade_no,
    DROP COLUMN IF EXISTS external_order_no,
    DROP COLUMN IF EXISTS import_batch_no,
    DROP COLUMN IF EXISTS raw_transaction_id,
    DROP COLUMN IF EXISTS verify_status;

-- Drop raw_transactions table
DROP TABLE IF EXISTS raw_transactions;
```

---

## Task 8: Clean dev-tools/mysql-api-server.cjs

**Files:**
- Modify: `dev-tools/mysql-api-server.cjs`

- [ ] **Step 1: Remove OCR-related code**

Remove:
- Lines 59-66: PaddleOCR python candidates configuration
- Lines 1244-1326: parseOcrPreview(), parseOcrListPreview()
- Lines 1328-1333: findPaddlePython()
- Lines 1335-1350: saveOcrImage()
- Lines 1352-1404: runPaddleOcr()
- Lines 1406-1444: previewActualExpenseOcr()
- Line 2176: Route handler for POST /ocr-preview

- [ ] **Step 2: Remove bill-import-related code**

Remove:
- Lines 816-883: ensureActualExpenseSchema() — remove raw_transactions table creation and bill-import column migrations (keep actual_expenses core table creation/migration)
- Lines 998-1005: decodeBillBuffer()
- Lines 1007-1029: parseCsvLine()
- Lines 1031-1083: parseBillRows()
- Lines 1085-1096: classifyTransactionKind()
- Lines 1098-1107: transactionKindLabel()
- Lines 1109-1124: merchantCategoryMap()
- Lines 1126-1144: verifyBillRow()
- Lines 1146-1211: previewBillImport()
- Lines 1213-1242: confirmBillImport()
- Lines 2170, 2173: Route handlers for import-preview and import-confirm

---

## Task 9: Build and verify

- [ ] **Step 1: Build backend**

```bash
cd backend && mvn clean package -DskipTests
```

- [ ] **Step 2: Build frontend**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit and push**

```bash
git add -A
git commit -m "chore: remove OCR model-service, WeChat/Alipay bill import features"
git push
```

---

## Self-Review

1. **Spec coverage:** All 3 features covered — OCR model-service (Tasks 1,2), bill import (Tasks 1,3,4,6,7,8), config cleanup (Tasks 2,5). WeChat LOGIN explicitly preserved per user decision.
2. **No placeholders:** All steps have exact file paths, exact code, exact commands.
3. **Type consistency:** ActualExpenseService.BulkCreateResponse record is used by both the service and controller — kept in Task 3 and referenced in Task 4 Step 2.
