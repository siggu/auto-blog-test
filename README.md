# Pipedream을 이용한 블로그 자동 포스팅 테스트

## WorkFlow
<img width="200" height="602" alt="image" src="https://github.com/user-attachments/assets/4a668b21-89b9-4d46-af14-ee605eb1b43e" />

### 1. trigger

- 매일 아침 9시 트리거 작동

### 2. fetch_rss_feed

- 검색할 RSS 피드를 input에 입력([연합뉴스 최신기사](https://www.yna.co.kr/rss/news.xml))

- 여러 RSS 피드를 검색하고 날짜별로 정렬된 항목의 병합된 배열을 반환

### 3. check_posted_articles

- 구글 시트 계정을 input에 입력

  - A1 셀의 값을 모두 가져옴

### 4. select_new_article

- RSS 피드를 비교하고 게시되지 않은 게시물을 선택

### 5. create_blog_post

- WordPress에 새로운 포스트 작성

<br/>

## WordPress 사이트
https://siggu100.wordpress.com

<br/>

> 연합뉴스는 비상업적 블로그와 개인적인 용도로만 연합뉴스 RSS 피드를 사용하는 것을 허용합니다.
> 
> 연합뉴스의 사전 서면 허가 없이 RSS 서비스를 상업적으로 이용하는 것을 금지합니다.
>
> [연합뉴스 RSS 피드](https://www.yna.co.kr/rss/index)
