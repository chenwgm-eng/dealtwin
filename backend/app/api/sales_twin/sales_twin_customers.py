"""客户与联系人路由 — 社区版存根

社区版不提供客户管理 API。商业版（dealtwin-business）通过 @edition 注入扩展提供者
注册客户/联系人 CRUD 路由到 sales_twin_bp。

数据模型（Customer/Contact）仍保留在 app.models.database 中，避免 schema 分叉。
"""
# 社区版：无路由注册。商业版注入 edition provider 后由其注册客户管理路由。