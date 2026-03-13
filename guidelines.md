# Bank Admin Development Guidelines

## Project Overview and Core Functions

The Bank Admin application is a financial reconciliation site for SSCL (Shared Services Connected Ltd) staff. It provides tools for managing prisoner money at a central level, focusing on transaction processing, refunds, and general ledger reconciliation.

### Core Functionalities
- **ADI Journal Generation**: Create journals for uploading to Oracle Social Care Finance (ADI) to record prisoner money transactions in the general ledger.
- **Refunds Processing**: Generate files (AccessPay format) to process refunds for credits that cannot be applied.
- **Bank Statement Downloads**: Generate bank statement files in MT940 format for reconciliation.
- **Disbursements**: Manage and process outgoing payments (disbursements) from prisoners to external bank accounts.
- **Operational Monitoring**: Visibility into missed or pending financial tasks for the preceding workdays.

## Application Architecture

The project is built with **Django** and relies on the `money-to-prisoners-api` for its data and core business logic. It also integrates with standard HMPPS/Gov.UK services.

### Key Integrations
The application interacts with several APIs and libraries:

- **MTP API (`money-to-prisoners-api`)**:
  - Central data store and authentication provider.
  - Used for fetching transactions, credits, and disbursements.
- **HMPPS Auth**:
  - Used for authenticating staff accounts via the MTP API.
- **GOV.UK Notify**:
  - Sends email notifications for disbursements and private estate emails.
- **GOV.UK Bank Holidays**:
  - Used for determining workdays for financial reconciliation via `mtp_common`.
- **Zendesk**:
  - For handling support tickets and feedback.

### Key Project Apps
- **`bank_admin` (`mtp_bank_admin.apps.bank_admin`)**: Core logic for ADI, refunds, statements, and disbursements.
- **`feedback` (`mtp_bank_admin.apps.feedback`)**: Logic for user feedback.
- **`mtp_common`**: Shared library for consistent styling, utilities, and common logic.

### Referenced Bespoke Packages
- **`mt940-writer`**: Maintained by the MTP team for generating bank statement files.
- **`django-moj-irat`**: For incident reporting and tracking.
- **`django-zendesk-tickets`**: For support ticket integration.

## Build and Configuration

- **Environment**: Requires Python 3.12+ and Node.js 24+.
- **Virtual Environment**: Use a Python virtual environment to isolate dependencies.
  ```shell
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Dependencies**: Managed via `run.py`. To update all dependencies:
  ```shell
  ./run.py dependencies
  ```
- **Configuration**:
  - Connects to the API (default `http://localhost:8000`).
  - Local settings can be overridden in `mtp_bank_admin/settings/local.py` (copy from `local.py.sample`).
- **Management Script**: `run.py` is the primary interface for development tasks.
  - `./run.py serve`: Start development server with live-reload (BrowserSync on `:3002`, Django on `:8002`).
  - `./run.py start`: Start development server without live-reload.
  - `./run.py --verbosity 2 help`: List all available build tasks.

## Access and Login

- **URL**: Once running, the application is accessible at [http://localhost:8002/](http://localhost:8002/).
- **API Requirement**: The `money-to-prisoners-api` must be running for Bank Admin to function.
- **Local Dev Login**: Use credentials `refund-bank-admin` or `disbursement-bank-admin` with the default password configured in your local API setup (usually the same as the username).

## User Setup (in MTP API)

To allow a user to log into Bank Admin, they must be set up in the `money-to-prisoners-api` with the following:

### Roles and Groups
Users should be assigned one of the following roles based on their required access:

1.  **Bank Admin (Refunds & Statements)**:
    - **Role**: `bank-admin`
    - **Groups**: `BankAdmin` AND `RefundBankAdmin`
    - **Permissions**: Grants access to ADI journals, bank statements, and refund files.

2.  **Disbursement Admin**:
    - **Role**: `disbursement-admin`
    - **Group**: `DisbursementBankAdmin`
    - **Permissions**: Grants access to processing and downloading disbursements.

### Application Mapping
- The user must be mapped to the **Bank admin** application (`bank-admin` client ID).

### Prison Mapping
- Prison mapping is **not required** for Bank Admin roles as they typically have global visibility into transactions (`view_any_credit` or `view_disbursement` permissions).

## Testing

### Running Tests
- **Full Suite**: Use `./run.py test`. This includes building assets and running Django tests.
- **Django Tests Only**: Run `manage.py test` directly:
  ```shell
  ./manage.py test bank_admin
  ```

## Additional Development Information

- **Frontend Assets**:
  - Assets are located in `mtp_bank_admin/assets-src/`.
  - Built assets are placed in `mtp_bank_admin/assets/`.
  - Use `./run.py build` to compile assets (SASS and JavaScript).
- **Translations**:
  - Update messages with `./run.py make_messages`.
- **Excel Templates**:
  - ADI and Disbursement templates (Excel format) are located in `local_files/`. These are used as bases for generated journals and disbursement files.
- **Docker**:
  - Run with `./run.py local_docker` for a production-like environment.
