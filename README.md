# n8n을 이용한 블로그 자동 포스팅 테스트

## WorkFlow
<img width="1542" height="314" alt="image" src="https://github.com/user-attachments/assets/a97d2a6f-31f6-47f8-a765-0753925efc50" />

### 1. Schedule Trigger

- Trigger Rules

  - Trigger Interval: Minutes
  - Minutes Between Triggers: 5

### 2.1 RSS Read

- URL: https://www.yna.co.kr/rss/news.xml

### 2.2 Google Sheets

- Operation: Get Row(s)

### 3. Merge

- Mode: SQL Qeury
- Number of Inputs: 2

### 4. Limit

- Max Items: 1
- Keep: First Items

### 5. HTTP Request

- Method: GET
- URL: `{{ $json.link }}`

### 6. HTML

- Operation: Extract HTML Content
- Source Data: JSON
- JSON Property: data
- Extraction Values
  - Key: extractedContent
  - CSS Selector: article
  - Return Value: HTML

### 7. Code

- Mode: Run Once for All Items
- Language: JavaScript

### 8. Send email

- Operation: Send

### 9. Append row in sheet

> Version 1.108.2

<br/>

> 연합뉴스는 비상업적 블로그와 개인적인 용도로만 연합뉴스 RSS 피드를 사용하는 것을 허용합니다.
> 
> 연합뉴스의 사전 서면 허가 없이 RSS 서비스를 상업적으로 이용하는 것을 금지합니다.
>
> [연합뉴스 RSS 피드](https://www.yna.co.kr/rss/index)
