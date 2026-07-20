# Excel — detected tables

Detected **2** table(s) across **1** sheet(s).

## Sheet: `2. Payment Process` — 2 table(s)

### Table 1 `[E2:G5]` — Chatbot - Smart Catbot System - Test cases: Payment Process SRS: https://tokyotechies.kleversuite.net/wiki/104-5581 New Sign Up Flow (without input Credit Card): https://tokyotechies.kleversuite.net/wiki/KOTAEDOC-8928

| Total testcase | 10 | Figma: |
|---|---|---|
| Pass | 2 | Bug: https://tokyotechies.kleversuite.net/project/CHAT-29437 |
| Fail | 0 |  |
| Pending | 0 |  |

### Table 2 `[A6:M20]`

> 🧮 **No** = IF(Expected="","","TC_"&ROW() - 7 - COUNTBLANK(Expected))  (`=IF(H8="","","TC_"&ROW()-7-COUNTBLANK(H8:H$9))`)

#### Free Trial Registration `[A7:M9]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_1 | SU-05 SU-06 SU-07 | UI | Happy Case | Start Free Trial | Login the first time after account verified | 1. Login for the first time 2. Click Subscribe button | 1. Direct to Plan Selection Screen Screen 2. Direct to Dashboard Screen | Pass |  |  |  |  |
| TC_2 | SU-05 SU-06 SU-07 | UI | Abnormal Case | Switch to Free Trial of other Pricing Plan among first 30 using days |  | 1. Login for the first time 2. Go to Account Settings > Billing > Select another Pricing Plan > Click Submit | 1. Direct to Start Your Free Trial Now Screen 2. New Pricing Plan will take effect with continuous free trial billing cycle (30 days) | Pass |  |  |  |  |

#### Continue Subscription `[A10:M13]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_3 | - |  | Happy Case | Continue subscription after Free Trial ends with valid card | - Register Free Trials successfully - Free Trials ends - Credit Card has edequate amount of money | 1. Login to system  2. Select Pricing Plan 3. Input  - Card Information  - Card holder name  - Country or region  4. Click Subscribe button | 1. Direct to Billing Screen (other screens are inaccessible) 2. Pricing Plan is selected 3. Credit Card information is inputted 4. Verify the Next End Date is next 30 days Verify the amount payment of Invoice history is same with Pricing Plan | Pass |  |  |  |  |
| TC_4 | - |  | Happy Case | Continue subscription after Subscription ends with valid card | - Register Free Trials successfully - Next Subscription successfully - Free Trials ends - Credit Card has edequate amount of money | 1. Login to system after renew subscription successfully 2. Click Settings in Left Side menu 3. Click Manage Billing button in Billing section 4. Confirm the Next End date & Invoice History | 1. Direct to Dashboard Screen 2. Direct to Reset Password and Billing Screen 3. Direct to Billing Management Screen 4. Verify the Next End Date is next month Verify the amount payment of Invoice history is same with Pricing Plan | Pass |  |  |  |  |
| TC_5 | - |  | Abnormal Case | Continue subscription after Subscription ends with INvalid card | - Register Free Trials successfully - Free Trials ends - Credit Card does not have edequate amount of money | 1. Login to system after renew subscription UNsuccessfully 2. Enter valid Credit Card | 1. Direct to Re-subscription Screen Other screens are grayout and un-accessible 2. After re-subscription successfully, all screens are accessible | Pass |  |  |  |  |

#### Cancel Subscription `[A14:M16]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_6 | - |  | Happy Case | Cancel subscription during Subscription with valid card | - Register Free Trials successfully - Free Trials in period - Credit Card has edequate amount of money | 1. Login to system after renew subscription successfully 2. Click Settings in Left Side menu 3. Click Manage Billing button in Billing section 4. In Current Plan section, click Cancel plan button 5. Click Cancel plan button 6. Select reason option, enter Feedback, click Submit button 7. Confirm information in Current Plan section | 1. Direct to Dashboard Screen 2. Direct to Reset Password and Billing Screen 3. Direct to Billing Management Screen 4. Direct to Cancel your plan screen 5. Cancel Subscription dialog appears 6. Direct to Billing Management Screen 7. Verify the End date of current plan Renew plan button appears | Pass |  |  |  |  |
| TC_7 | - |  | Happy Case | Subscription ends | - Cancel subscription successfully - Subscription ends - Credit Card has edequate amount of money | 1. Login to system after renew subscription UNsuccessfully 2. Confirm Credit Card | 1. Direct to Re-subscription Screen Other screens are grayout and un-accessible? 2. No charge in Credit Card | Pass |  |  |  |  |

#### Renew Subscription `[A17:M20]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_8 | - |  | Happy Case | Renew subscription during Subscription with valid card | - Cancel subscription successfully - Free Trials in period - Credit Card has edequate amount of money | 1. Login to system after cancel subscription successfully 2. Click Settings in Left Side menu 3. Click Manage Billing button in Billing section 4. In Current Plan section, click Renew plan button 5. Click Renew plan button 6. Confirm information in Current Plan section | 1. Direct to Dashboard Screen 2. Direct to Reset Password and Billing Screen 3. Direct to Billing Management Screen 4. Direct to Renew your plan screen 5. Direct to Billing Management Screen 6. Verify the End date of current plan Cancel plan button appears | Pass |  |  |  |  |
| TC_9 | - |  | Happy Case | Renew subscription after Subscription ends | - Cancel subscription successfully - Subscription ends - Credit Card has edequate amount of money | 1. Login to system after renew subscription UNsuccessfully 2. Confirm Credit Card | 1. Direct to Dashboard Screen Other screens are accessible? 2. Charge correct amount of money in Credit Card | Fail |  |  |  |  |
| TC_10 | - |  | Happy Case | Renew subscription after cancel Subscription with valid card | - Cancel subscription successfully - Subscription ends - Credit Card has edequate amount of money | 1. Login to system after cancel subscription successfully & Subscription ends 2. Enter valid Credit Card | 1. Direct to Re-subscription Screen Other screens are grayout and un-accessible? 2. After re-subscription successfully, all screens are accessible | Pass |  |  |  |  |

