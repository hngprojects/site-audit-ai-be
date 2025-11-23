[Unit]
Description=SiteMate AI Backend (${DEPLOY_ENV})
After=network.target
Wants=network-online.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_ROOT}
EnvironmentFile=${APP_ROOT}/.env
ExecStart=${PYTHON_BIN} -m uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=30
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
