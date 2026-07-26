/**
 * DealTwin 社区版扩展注册表（@edition 存根）
 *
 * 社区版默认无客户管理/认证/RBAC 扩展。
 * 商业版（dealtwin-business）通过注入 setEditionProvider 启用扩展功能。
 *
 * 用法（商业版 main.js）：
 *   import { setEditionProvider } from './composables/salesTwin/edition'
 *   setEditionProvider(businessProvider)
 */

let _provider = null

export function setEditionProvider(provider) {
  _provider = provider
}

export function getEditionProvider() {
  return _provider
}

export function hasCustomerModule() {
  return _provider?.customerModuleEnabled === true
}

export function hasAuth() {
  return _provider?.authEnabled === true
}

export function getExtraMenuItems() {
  return _provider?.menuItems || []
}

export function getExtraRoutes() {
  return _provider?.routes || []
}