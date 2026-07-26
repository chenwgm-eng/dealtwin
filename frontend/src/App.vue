<template>
  <router-view />
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #15171D;
  background-color: #F4F0E7;
}

/* 滚动条样式：柔和的暖灰色调 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #EBE7DC;
}

::-webkit-scrollbar-thumb {
  background: #D7D4CD;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #BCBFBD;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
