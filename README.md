# ansible-role-haproxy

Ansible-роль для установки и настройки HAProxy. Поддерживает Debian (apt), RHEL/CentOS (yum/dnf).

## Возможности

- Установка HAProxy из системных пакетов или официального репозитория Debian
- Разделение конфигурации на глобальную (`haproxy.cfg`) и прикладную (`conf.d/haproxy-app.cfg`)
- Валидация конфигурации перед применением с помощью `haproxy-validate-config`
- Настройка frontend/backend через переменные
- Поддержка SSL-сертификатов на frontend
- Кастомные страницы ошибок
- Map-файлы для маршрутизации
- Stats-страница с авторизацией
- Systemd override: `OOMScoreAdjust`, `Restart=on-failure`
- Утилита `haproxy-state` для мониторинга состояния через Unix-сокет

## Требования

- Ansible >= 2.10
- Python 3 на целевом хосте (для утилит валидации и мониторинга)

## Поддерживаемые платформы

| OS       | Версии           |
|----------|------------------|
| Debian   | Bookworm, Trixie |

## Установка

```bash
ansible-galaxy install git+https://github.com/mraops/ansible-role-haproxy.git
```

## Переменные

### Основные

| Переменная                            | Значение по умолчанию | Описание                                                  |
|---------------------------------------|-----------------------|-----------------------------------------------------------|
| `haproxy_add_official_haproxy_repository` | `false`               | Добавить официальный репозиторий HAProxy (Debian)         |
| `haproxy_debian_version`              | `"3.2"`               | Версия HAProxy из официального репозитория                |
| `haproxy_oom_score_adjust`            | `-900`                | OOM score для systemd                                    |
| `haproxy_restart_sec`                 | `5s`                  | Задержка перед рестартом сервиса при сбое                 |
| `haproxy_stats_user`                  | `haproxy`             | Логин для Stats-страницы                                  |
| `haproxy_stats_user_pass`             | `haproxy`             | Пароль для Stats-страницы                                 |
| `haproxy_maps_dir`                    | `/etc/haproxy/maps/`  | Директория для map-файлов                                 |

### Таймауты

| Переменная                  | По умолчанию | Описание                |
|-----------------------------|--------------|-------------------------|
| `haproxy_maxconn`           | `4096`       | Максимальное число соединений |
| `haproxy_retries`           | `3`          | Число попыток           |
| `haproxy_timeout_connect`   | `5s`         | Таймаут подключения     |
| `haproxy_timeout_client`    | `50s`        | Таймаут клиента         |
| `haproxy_timeout_server`    | `50s`        | Таймаут сервера         |
| `haproxy_timeout_queue`     | `30s`        | Таймаут очереди         |
| `haproxy_timeout_tunnel`    | `30m`        | Таймаут туннеля         |

### Frontend

```yaml
haproxy_frontends:
  - name: https_front
    bind: "*:443"
    ssl_enabled: true
    ssl_cert: "/etc/ssl/private/haproxy.pem"
    ssl_cert_src: "files/haproxy.pem"    # Путь к сертификату на управляющем хосте
    ssl_options: "no-sslv3"
    default_backend: web_backend
    options:
      - "option forwardfor"
      - "http-request set-header X-Forwarded-Proto https"
  - name: http_front
    bind: "*:80"
    default_backend: web_backend
    options:
      - "redirect scheme https code 301 if !{ ssl_fc }"
```

### Backend

```yaml
haproxy_backends:
  - name: web_backend
    balance: roundrobin        # Опционально, по умолчанию roundrobin
    options:                   # Опционально
      - "option httpchk GET /health"
    servers:
      - name: web1
        address: 10.0.0.101
        port: 80
      - name: web2
        address: 10.0.0.102
        port: 80
        options: "check inter 5s rise 2 fall 3"   # Опционально, по умолчанию "check"
```

### Map-файлы

```yaml
haproxy_maps:
  - name: hosts_map
    content:
      www.example.com: web_backend
      www.test.com: test_backend
```

## Пример использования

```yaml
- hosts: loadbalancers
  become: true
  roles:
    - role: ansible-role-haproxy
      vars:
        haproxy_frontends:
          - name: https_front
            bind: "*:443"
            ssl_enabled: true
            ssl_cert: "/etc/ssl/private/haproxy.pem"
            ssl_cert_src: "files/haproxy.pem"
            default_backend: web_backend
            options:
              - "option forwardfor"
              - "http-request set-header X-Forwarded-Proto https"
          - name: http_front
            bind: "*:80"
            default_backend: web_backend
            options:
              - "redirect scheme https code 301 if !{ ssl_fc }"
        haproxy_backends:
          - name: web_backend
            balance: roundrobin
            servers:
              - name: web1
                address: 10.0.0.101
                port: 80
              - name: web2
                address: 10.0.0.102
                port: 80
```

## Теги

| Тег                     | Описание                              |
|-------------------------|---------------------------------------|
| `haproxy-install`       | Установка пакета                      |
| `haproxy-config`        | Вся конфигурация                      |
| `haproxy-global-config` | Только глобальный `haproxy.cfg`       |
| `haproxy-app`           | Только прикладная конфигурация        |
| `haproxy-ssl`           | Копирование SSL-сертификатов          |
| `haproxy-maps`          | Генерация map-файлов                  |
| `haproxy-tools`         | Копирование утилит                    |
| `haproxy-upload-errors` | Загрузка страниц ошибок               |
| `haproxy-start`         | Запуск и включение сервиса            |

Пример запуска с тегами:

```bash
# Только обновить конфигурацию приложения
ansible-playbook playbook.yml --tags haproxy-app

# Только обновить SSL-сертификаты
ansible-playbook playbook.yml --tags haproxy-ssl
```

## Утилиты

### haproxy-validate-config

Валидирует конфигурацию HAProxy перед применением. Проверяет основной конфиг вместе с директорией `conf.d`. При необходимости подставляет кандидат-файл вместо существующего.

```bash
# Проверка всей конфигурации
haproxy-validate-config --main-config /etc/haproxy/haproxy.cfg --conf-dir /etc/haproxy/conf.d

# Проверка с подстановкой кандидат-файла
haproxy-validate-config \
  --main-config /etc/haproxy/haproxy.cfg \
  --conf-dir /etc/haproxy/conf.d \
  --candidate-config /tmp/haproxy-app.cfg \
  --candidate-name haproxy-app.cfg
```

### haproxy-state

Показывает состояние frontend/backend/server через stats-сокет HAProxy.

```bash
# Полное состояние
haproxy-state

# Только нездоровые серверы
haproxy-state --down

# JSON-вывод
haproxy-state --json

# Автообновление каждые 5 секунд
haproxy-state --watch 5

# Указать другой сокет
haproxy-state --socket /var/run/haproxy.sock
```

## Структура конфигурации на хосте

```
/etc/haproxy/
├── haproxy.cfg              # Глобальная конфигурация (global, defaults, stats)
├── conf.d/
│   └── haproxy-app.cfg      # Frontend/Backend конфигурация
├── errors/                  # Кастомные страницы ошибок
└── maps/                    # Map-файлы
```
