# Excel — detected tables

Detected **3** table(s) across **1** sheet(s).

## Sheet: `4. Chatbot` — 3 table(s)

### Table 1 `[E2:G5]` — Chatbot - Smart Catbot System - Test cases: Chatbot SRS: https://tokyotechies.kleversuite.net/wiki/104-5581

| Total testcase | 46 | Figma: |
|---|---|---|
| Pass | 20 | Bug: https://tokyotechies.kleversuite.net/project/CHAT-28672 |
| Fail | 7 |  |
| Pending | 0 |  |

### Table 2 `[A6:M65]` — Escalated Support: https://tokyotechies.kleversuite.net/wiki/KOTAEDOC-8058

#### Chatbot Integration `[A7:M9]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_1 | - | UI | Integrate chatbot | Integrate chatbot to website |  |  | - Display normally in integrated website - Chatbot works normally in integrated website | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-30017 |  |
| TC_2 | - |  | Chatbot's UI updates | Chatbot's UI updates after update Chatbot's Configuration |  |  | - Display updated UI normally in integrated website - Chatbot works normally in integrated website | Pass |  |  |  |  |

#### Chatbot Behaviors `[A10:M39]`

##### Train chatbot with Website URL `[A11:M19]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_3 |  |  | Ask question about Website URL before submit initial Website URL |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_4 |  |  | Ask question after submit initial Website URL |  |  |  | Answer properly | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-29399 |  |
| TC_5 |  |  | Ask question belongs to new Website URL after update new Website URL |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_6 |  |  | Ask question belongs to previous Website URL after update new Website URL |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_7 |  |  | Ask question with conflict answers in previous & new Website URL after update new Website URL |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_8 |  |  | Ask question about Website URL with conflict answers inside Website |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_9 |  |  | Ask question with similar meaning of questions in Website URL |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_10 |  |  | Ask question with Long question & Long answer, Maximum file size, Complex site map, different languages |  |  |  | Answer properly | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-29784 |  |

##### Train chatbot with File Data `[A20:M26]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_11 |  |  | Ask question after upload single file |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_12 |  |  | Ask question after upload single file with different answers inside file |  |  |  | Answer properly | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-29773 |  |
| TC_13 |  |  | Ask question after upload multiple files |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_14 |  |  | Ask question after upload multiple files with different answers inside files |  |  |  | Answer properly | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-29773 |  |
| TC_15 |  |  | Ask question with similar meaning of questions in File Data |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_16 |  |  | Ask question with Long question & Long answer, Maximum file size, Complex site map, different languages |  |  |  | Answer properly | Fail |  |  | https://tokyotechies.kleversuite.net/project/CHAT-29784 |  |

##### Train chatbot with FAQs `[A27:M31]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_17 |  |  | Ask question in FAQs |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_18 |  |  | Ask question with similar meaning of questions in FAQs |  |  |  | Answer properly | Pass |  |  |  |  |
| TC_19 |  |  | Ask question with same questions but different answers in FAQs |  |  |  | Prioritize newest answer in FAQs | Fail |  |  |  |  |
| TC_20 |  |  | Ask question with Long question & Long answer, Maximum file size, Complex site map, different languages |  |  |  | Answer properly | Pass |  |  |  |  |

##### Train chatbot with Website URL + File Data `[A32:M33]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_21 |  |  | Ask question with same questions but different answers in resources |  |  |  | Provide both answers from 2 resources |  |  |  |  |  |

##### Train chatbot with Website URL + FAQ `[A34:M35]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_22 |  |  | Ask question with same questions but different answers in resources |  |  |  | Prioritize answer from FAQs | Pass |  |  |  |  |

##### Train chatbot with File data + FAQ `[A36:M37]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_23 |  |  | Ask question with same questions but different answers in resources |  |  |  | Prioritize answer from FAQs | Pass |  |  |  |  |

##### Train chatbot with Website URL + File Data + FAQ `[A38:M39]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_24 |  |  | Ask question with same questions but different answers in resources |  |  |  | Prioritize answer from FAQs | Pass |  |  |  |  |

#### Escalated Support `[A40:M46]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_25 |  |  | Ask for Escalated Support and complete the flow | Fill all in required fields |  |  | - Successfully send the escalated support request - In Analytics page, the escalated request displays - In chat history, the question is marked as Escalated - Email sends to user - Email sends to admin |  |  |  |  |  |
| TC_26 |  |  | Ask for Escalated Support and complete the flow | Fill over max length in each fields |  |  | Error Message displays |  |  |  |  |  |
| TC_27 |  |  | Ask for Escalated Support and complete the flow | Fill empty in required fields |  |  | Error Message displays |  |  |  |  |  |
| TC_28 |  |  | Ask for Escalated Support and stop at the middle of the flow | Stop flow after click Escalated Support |  |  | - Unsuccessfully send the escalated support request |  |  |  |  |  |
| TC_29 |  |  | Ask for Escalated Support and stop at the middle of the flow | Stop flow after click No in Escalated Flow Notification |  |  | - Unsuccessfully send the escalated support request |  |  |  |  |  |
| TC_30 |  |  | Ask for Escalated Support and stop at the middle of the flow | Stop flow after click Yes in Escalated Flow Notification |  |  | - Unsuccessfully send the escalated support request |  |  |  |  |  |

#### Thumb up/ down the answer `[A47:M54]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_31 |  |  | Thumbs up an answer |  |  |  | - The answer is thumbed up - In chat history, the thumb up displays for the answer |  |  |  |  |  |
| TC_32 |  |  | Un-thumbs up an answer |  |  |  | - The answer is not given any thumb ub - In chat history, the thumb up disappear for the answer |  |  |  |  |  |
| TC_33 |  |  | Thumbs down an answer |  |  |  | - The answer is thumbed down - In chat history, the thumb down displays for the answer |  |  |  |  |  |
| TC_34 |  |  | Un-thumbs down an answer |  |  |  | - The answer is not given any thumb down - In chat history, the thumb down disappear for the answer |  |  |  |  |  |
| TC_35 |  |  | Thumbs up then thumbs down an answer |  |  |  | - The answer is thumbed down - In chat history, the thumb down displays for the answer |  |  |  |  |  |
| TC_36 |  |  | Thumbs down then thumbs up an answer |  |  |  | - The answer is thumbed up - In chat history, the thumb up displays for the answer |  |  |  |  |  |
| TC_37 |  |  | Ask multiple questions, then thumbs up/down for multiple answers |  |  |  | - Each answer is thumbed up or down corresponding - In chat history, the thumb up or down displays for the answer corresponding |  |  |  |  |  |

#### Ask questions related to keywords `[A55:M60]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_38 |  |  | Ask questions related to keywords only |  |  |  | In chatbot's answer, display the keyword to the link (when click the link it opens in other tab) |  |  |  |  |  |
| TC_39 |  |  | Ask questions related to keywords and Website data |  |  |  | In chatbot's answer, display all keyword Note: The Priority is: - Keywords - FAQ - Website/ File Data |  |  |  |  |  |
| TC_40 |  |  | Ask questions related to keywords and file data |  |  |  | In chatbot's answer, display all keyword |  |  |  |  |  |
| TC_41 |  |  | Ask questions related to keywords and FAQ's data |  |  |  | In chatbot's answer, display all keyword |  |  |  |  |  |
| TC_42 |  |  | Ask questions related to keywords and Website, file, FAQ's data |  |  |  | In chatbot's answer, display all keyword |  |  |  |  |  |

#### Notification Emails `[A61:M65]`

| No | Requirement ID | Type | Test case | Sub cases | Precondition | Step | Expected | Pass/Fail | Tester | Test Date | Remarks | Auto e2e |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_35 |  |  | Chatbot Capicity Usage of the month | Use chatbot when reach 80% capacity of usage for the month |  | 1. Login to sytem 2. Use the chatbot and send the message reach 80% capacity of usage for the month | Chatbot is still usable | Pass |  |  |  |  |
| TC_36 |  |  | Chatbot Capicity Usage of the month | Use chatbot when reach Maximum capacity of usage for the month |  | 1. Login to sytem 2. Use the chatbot and send the message reach 80% capacity of usage for the month | Chatbot is still not usable. When chat with chatbot, chatbot will answer:  "Sorry, we are under maintenance!" | Pass |  |  |  |  |
| TC_37 |  |  | Escalated Conversation | Email notification to the end user who asked for the hand over to human |  | Chatbot UI > "talk to human" button > Receive escalation copy email | https://tokyotechies.kleversuite.net/wiki/KOTAEDOC-7605 | Pass |  |  |  |  |
| TC_38 |  |  | Escalated Conversation | Email notification of escalated conversation to business owner |  | Chatbot UI > "talk to human" button > Receive escalation copy email | same as above | Pass |  |  |  |  |


### Table 3 `[A69:B70]` — Bug:

| Their > Our | https://tokyotechies.kleversuite.net/project/CHAT-30258 |
|---|---|
| Where are you? | https://tokyotechies.kleversuite.net/project/CHAT-33840 |
