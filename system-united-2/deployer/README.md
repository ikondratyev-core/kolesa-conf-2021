Desctiption
=========

Новая версия system-united (2.0) :D

## Structure  
```
.
├── values.yaml (file for servicies)
├── jobs.yaml (file for jobs)
├── secrets.yaml (file for secrets)
├── cronjobs.yaml (file for cronjobs)
├── configmaps.yaml (file for configmaps)
└── README.md
```  

Examples (values.yaml)
------------

Пример нескольких приложений:

    services:
    - name: pod-one
      image: nginx:1.13
      ports:
      - name: http
        port: 80
    - name: pod-two
      image: nginx:1.13
      ports:
      - name: http
        port: 80

Минимальное описание приложения
------------

Минимальное описание сервиса, создается Deployment без Service, проверки выключены:

    services:
    - name: pod-minimal 
      image: nginx:1.14
      livenessProbe:
        dislabed: true
      readinessProbe:
        dislabed: true

Service (values.yaml)
--------------

Создается динамически если есть блок - ports.

Deployment (values.yaml)
--------------

Пример использования Deployment c несколькими портами, Service создастся с каждым портом:

    services:
    - name: pod-minimal
      image: nginx:1.14
      ...
      ports:
      - name: http
        port: 80
      - name: https
        port: 443
      ...

Пример использования переменных Envintoment:

    services:
    - name: pod-minimal
      image: nginx:1.14
      env:
      - name: DB_HOST
        value: 192.168.10.10
      - name: DB_USER
        value: db_user

Пример использования ресурсов, если их не указать есть значения по умолчанию:
limits - cpu:100m, memory:256Mi, requests - cpu:100m, memory:128Mi

    services:
    - name: pod-minimal
      image: nginx:1.14
      ...
      resources:
        limits:
          cpu: 200m
          memory: 512Mi
        requests:
          cpu: 100m
          memory: 256Mi
      ...

Проверки livenessProbe, readinessProbe, их выключение описано в первом примере (Service).
По умолчанию если создан блок ports, подставятся значения первого! порта в блоке ports.
Пример переопределения параметров, httpGet указан в качестве примера, можно использовать все что угодно, подробнее в доке:
https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/

    services:
    - name: pod-minimal
      image: nginx:1.14
      ...
      livenessProbe:
        httpGet:
          path: /service/alive
          port: http
      readinessProbe:
        httpGet:
          path: /service/alive
          port: http
      ...

Монтирование, обязательно нужно указать volumeMounts и volumes, привязываеются к значению name, пример hostPath:

    services:
    - name: pod-minimal
      image: nginx:1.14
      ...
      volumeMounts:
      - name: timezone
        mountPath: /etc/localtime
        readOnly: true
      volumes:
      - name: timezone
        hostPath:
          path: /usr/share/zoneinfo/Asia/Almaty
      ...

Монтирование, обязательно нужно указать volumeMounts и volumes, привязываеются к значению name, пример PV, PVC:

    services:
    - name: pod-minimal
      image: nginx:1.14
      ...
      volumeMounts:
      - name: data
        mountPath: /tmp/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: test-pvc
      ...

Blue green deployment (пока не подниметься новый pod, не выключать старый) и изменение количества реплик.
По умолчанию rollingUpdate настроен на удаления старого pod после обновления.
По умолчанию количество replicas - 1.
Изменить можно следующим образом:

    services:
    - name: pod-minimal
      image: nginx:1.14
      perlicas: 2
      ...
      rollingUpdate:
         maxSurge: 1
         maxUnavailable: 0
      ...

Ingress (values.yaml)
--------------

Минимальная запись для добавление хоста в nginx:

    services:
    - name: pod-ingress
      image: nginx:1.14
      ...
      ingress:
      - host: example.domain.kz
      ...                       

Параметры по умолчанию (которые можно переопределить):

path: /

Параметы не переопределяемые (вычисляются автоматически):

serviceName: название сервиса, блок name (pod-ingress)
servicePort: первый! порт в блоке ports (80), если нужен 443, то нужно поменять порядок портов в блоке ports.

    services:
    - name: pod-ingress
      image: nginx:1.14
      ...
      ports:
      - name: http
        port: 80
      - name: https
        port: 443
      ingress:
      - host: example.domain.kz
        path: /example
      ... 

Пример добавления нескольких хостов к одному сервису

    services:
    - name: pod-ingress
      image: nginx:1.14
      ...
      ports:
      - name: http
        port: 80
      ingress:
      - host: example.domain.kz
      - host: example2.domain.kz
      ...

Пример использования SSL:

    services:
    - name: pod-ingress
      image: nginx:1.14
      ...
      ports:
      - name: http
        port: 80
      ingress:
      - host: example.domain.kz
        tls:
           secretName: egs-tls
      - host: example2.domain.kz
        tls:
           secretName: egs2-tls
      ....

Secrets (secrets.yaml)
--------------

## Использование docker registry secret
```
  secrets:
  ...
    dockerconfigjson: 
    - name: default-registry
      value: "token-value"
  ...
```
```
  secrets:
  ...
    dockerconfigjson: 
    - name: registry1
      value: "token-value"
    - name: registry2
      value: "token-value"
  ...
```
## Использование SSL сертификата (TLS)
```
  secrets:
  ...
    tls:
    - name: egs-tls
      crt: certificate (base64)
      key: certificate key (base64)
  ...
```

Configmap (configmaps.yaml)
--------------

## Использование одного конфига или нескольких:
```
  configmaps:
  ...
  - name: nginx2.conf
    data: |+
      my configmaps
      worker_processes auto;
      error_log /dev/stdout info;
      pid /run/nginx.pid;
```
```
  configmaps:
  ...
  - name: nginx2.conf
    data: |+
      my configmaps
      worker_processes auto;
      error_log /dev/stdout info;
      pid /run/nginx.pid;
  - name: nginx3.conf
    data: |+
      my configmaps123
      worker_processes auto;
      error_log /dev/stdout info;
      pid /run/nginx.pid; 
```

Cronjobs (cronjobs.yaml)
--------------

## Использование одного или нескольких крон задач:

```
cronjobs:
  ...
  - name: my-job1
    schedule: "*/20 * * * *"
    image: git-registry.thefroot.com/thefroot/thefroot-backend:1.1.0-191-87a88c7
    args:
    - /bin/sh
    - -c
    - /usr/bin/php /var/www/thefroot/current/yii eu-bank/change-status
    env:
    - name: "DB_HOST"
      value: "192.168.60.14"
    - name: "DB_NAME"
      value: "db_thefroot"
    - name: "DB_PASSWORD"
      value: "2DnyPaEnQQTJP3E4"
    - name: "DB_USERNAME"
      value: "db_thefroot"
  ...
```
```
cronjobs:

  - name: my-job1
    schedule: "*/20 * * * *"
    image: git-registry.thefroot.com/thefroot/thefroot-backend:1.1.0-191-87a88c7
    args:
    - /bin/sh
    - -c
    - /usr/bin/php /var/www/thefroot/current/yii eu-bank/change-status
    env:
    - name: "DB_HOST"
      value: "db_host"
    - name: "DB_NAME"
      value: "db_thefroot"
    - name: "DB_PASSWORD"
      value: "db_password"
    - name: "DB_USERNAME"
      value: "db_thefroot"

  - name: my-job2
    schedule: "15 2 * 3 *"
    image: git-registry.thefroot.com/thefroot/thefroot-backend:1.1.0-191-87a88c7
    env:
    - name: "DB_HOST"
      value: "db_host"
    - name: "DB_NAME"
      value: "db_thefroot"
    - name: "DB_PASSWORD"
      value: "db_password"
    - name: "DB_USERNAME"
      value: "db_thefroot"
```
