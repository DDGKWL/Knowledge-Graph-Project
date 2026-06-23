const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
    transpileDependencies: true,
// 1. 调试配置：让你在控制台报错时能直接定位到 .vue 源码文件
    configureWebpack: {
        devtool: "eval-cheap-module-source-map",
    },

    // 2. 开发服务器配置
    devServer: {
        port: 8081, // 固定当前前端端口
        proxy: {
            // 代理逻辑：把除了热更新之外的所有接口请求转给后端
            "^(?!/ws|/sockjs-node)": {
                target: "http://localhost:5001", // 这里确认是你 Python 后端的端口
                changeOrigin: true,
                ws: false,
            },
        },
        client: {
            // 关键：明确告诉前端，热更新的信号去 8081 找，不要去后端找
            webSocketURL: "ws://localhost:8081/ws",
        },
    },
})
