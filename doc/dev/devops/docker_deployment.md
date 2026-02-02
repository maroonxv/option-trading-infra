# Docker 部署与 MySQL 依赖管理方案

## 1. 概述
本项目依赖 MySQL 数据库进行行情记录与策略状态回放。使用 Docker 进行容器化部署是完全可行的，并且是推荐的标准做法。通过 `Docker Compose` 编排，可以将策略应用与数据库服务打包在一起，实现“一键启动”。

## 2. 部署架构
我们将采用 **“统一镜像，多服务编排”** 的架构，所有 Python 服务共享同一个镜像，但通过启动命令区分角色：

1.  **数据库服务 (`mysql-db`)**
    *   **基础镜像**: `mysql:8.0`
    *   **功能**: 提供数据存储，支持通过 `init.sql` 自动初始化数据。

2.  **监控面板服务 (`dashboard`)**
    *   **功能**: 运行 Web 界面，端口映射 `5007`。
    *   **依赖**: `mysql-db`。

3.  **策略服务组 (`strategy-15m`, `strategy-1h`...)**
    *   **功能**: 每个时间周期的策略运行在独立的容器中（1+N 模式）。
    *   **配置**: 挂载宿主机 `config/` 目录，通过命令行参数加载特定配置文件。
    *   **依赖**: `mysql-db`。

## 3. 核心问题解决方案

### 3.1 如何处理 MySQL 依赖？
在 Docker 环境中，策略不再连接 `localhost` 或 `127.0.0.1`，而是连接 `docker-compose.yml` 中定义的**服务名称**。

*   **网络配置**:
    在 Docker 网络中，服务名（如 `mysql-db`）会自动解析为容器的 IP 地址。
    因此，策略配置文件（如 `.env` 或 `config/strategy_config.yaml`）中的 `database.host` 需要修改为 `mysql-db`。

*   **驱动安装**:
    `Dockerfile` 会自动执行 `pip install -r requirements.txt`，其中已包含 `vnpy_mysql` 和 `pymysql`，确保应用容器拥有连接数据库的能力。

### 3.2 现有数据如何随部署迁移？
数据库中的数据（K线、策略状态）是文件系统之外的状态，需要特殊处理。

#### 方案：数据导出与自动初始化（Init Script）—— 推荐用于打包交付
如果希望把当前的数据库“快照”打包带走，部署到新机器上时自带数据。

*   **操作步骤**:
    1.  **导出**: 在当前环境使用 `mysqldump` 导出数据为 `init.sql`。
    2.  **配置**: 将 `init.sql` 放入 Docker 镜像或挂载到 `/docker-entrypoint-initdb.d/`。
*   **原理**: MySQL 官方镜像在首次启动时，会自动执行该目录下的 SQL 文件。
*   **优点**: 完美实现“数据随镜像走”，适合迁移到全新环境。


## 4. 推荐实施路径


1.  **目录结构规范**:
    *   建立 `deploy/` 目录存放 Docker 相关文件。
    *   建立 `deploy/init_data/` 存放导出的 `init.sql`。

2.  **环境增强 (Dockerfile)**:
    *   基础镜像保持 `python:3.10-slim`。
    *   **关键**: 必须安装 `tzdata` 并设置时区为 `Asia/Shanghai`，确保 K 线时间准确。
    *   **关键**: 必须生成 `zh_CN.UTF-8` Locale，确保 CTP 接口在 Linux 下正常工作。

3.  **服务编排 (Compose)**:
    *   编写静态的 `docker-compose.yml`。
    *   显式定义 `mysql-db`, `dashboard` 和初始的 `strategy-15m` 服务。
    *   后续增加策略只需复制粘贴 Service 块并修改配置文件路径。

4.  **数据管理**:
    *   使用 **方案 B** (Init Script) 进行初始数据导入。
    *   使用 **方案 A** (Volume) 进行后续数据的持久化存储。

## 5. 配置文件关键点预览

### Dockerfile (deploy/Dockerfile)
*   **基础**: `python:3.10-slim`
*   **系统依赖**: 增加 `locales`, `tzdata`, `default-libmysqlclient-dev`。
*   **环境设置**:
    *   `ENV TZ=Asia/Shanghai`
    *   `ENV LANG=zh_CN.UTF-8`
*   **代码**: 复制项目根目录到 `/app`。

### docker-compose.yml (deploy/docker-compose.yml)
包含三个主要部分：
1.  **mysql-db**: 挂载 `./init_data:/docker-entrypoint-initdb.d` (初始化) 和 `mysql_data:/var/lib/mysql` (持久化)。
2.  **dashboard**: 启动命令 `python src/interface/web/app.py`，端口 `5007`。
3.  **strategy-15m**: 启动命令 `python src/main/main.py ... --override-config config/timeframe/15m.yaml`。
