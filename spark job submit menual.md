# [Spark job submit menual]
## 1. 설치하기
### 1-1 apache spark 사이트에서 버전과 패키지 지정 후 다운로드
### 1-2 apache hadoop 사이트에서 spark 버전에 맞는 hadoop 다운로드
### 1-3 spark와 hadoop의 환경변수 설정해주기
### 1-2-1 java가 없다면 java 8 or java 11 받고 환경변수까지 설정해주기
##  2. yaml/yml 파일 만들기
### 2-1. 코드에서 클러스터 만들어주기 (master, worker)
#### 예 :
      version: "3.9"  # Docker Compose 최신 버전
      services:
      spark-master:
          image: bitnami/spark:latest # 이미지 버전은 하둡같은 라이브러리와 함께 쓸때 지정(현재 최신버전)
          environment:
              - SPARK_MODE=master # 클러스터 역할 : 중앙관리 마스터
          ports:
              - "8080:8080"
              - "7077:7077"
          networks:
              - spark-network
          # 그 외의 속성들을 추가해서 구현하기 
      spark-worker:
          image: bitnami/spark:latest
          environment:
              - SPARK_MODE=worker
              - SPARK_MASTER_URL=spark://spark-master:7077
          depends_on:
              - spark-master
          networks:
              - spark-network
    
    
      spark-worker-2: #추가 작업수행 노드가 필요할때 주석지우기
          image: bitnami/spark:latest
          environment:
            - SPARK_MODE=worker
            - SPARK_MASTER_URL=spark://spark-master:7077
          depends_on:
            - spark-master
          networks:
            - spark-network
      networks:
      spark-network:
          driver: bridge
### 2-2. 클러스터의 속성 추가해 주기
## 3 spark-submit 명령어로 어플리케이션 제출하기
#### 예 :
      spark-submit
     --master spark://spark-master:7077 C:\Users\user\Desktop\git\BACKEND\apps\test.py ##master 클러스터 포트(standalone모드임 yarn 등등 클러스터로도 바꿀수 있음), py파일(어플) 위치 
     --deploy-mode cluster ## 클러스터 모드(클라이언트도 있음)
## 3-1 제출하고 처리한 결과 확인하기 (웹UI에서 port(local:8080))
### - 현재 이슈 처리 못하는중(앱 제출은 되나 받거나 처리가 안됨)