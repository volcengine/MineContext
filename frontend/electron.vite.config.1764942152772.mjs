// electron.vite.config.ts
import react from "@vitejs/plugin-react-swc";
import { CodeInspectorPlugin } from "code-inspector-plugin";
import { resolve } from "path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import { visualizer } from "rollup-plugin-visualizer";
import tailwindcss from "@tailwindcss/vite";
var visualizerPlugin = (type) => {
  return process.env[`VISUALIZER_${type.toUpperCase()}`] ? [visualizer({ open: true })] : [];
};
var isDev = process.env.NODE_ENV === "development";
var electron_vite_config_default = defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        "@main": resolve("src/main"),
        "@types": resolve("src/renderer/src/types"),
        "@shared": resolve("packages/shared"),
        "@logger": resolve("src/main/services/LoggerService")
      }
    }
  },
  preload: {
    plugins: [
      react({
        tsDecorators: true
      }),
      externalizeDepsPlugin()
    ],
    resolve: {
      alias: {
        "@shared": resolve("packages/shared"),
        "@types": resolve("src/renderer/src/types")
      }
    },
    build: {
      sourcemap: isDev
    }
  },
  renderer: {
    resolve: {
      alias: {
        "@renderer": resolve("src/renderer/src"),
        "@shared": resolve("packages/shared"),
        "@logger": resolve("src/renderer/src/services/LoggerService"),
        "@types": resolve("src/renderer/src/types")
      }
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true
        }
      }
    },
    plugins: [
      tailwindcss(),
      react({}),
      ...isDev ? [CodeInspectorPlugin({ bundler: "vite" })] : [],
      // 只在开发环境下启用 CodeInspectorPlugin
      ...visualizerPlugin("renderer"),
      {
        name: "force-arco-adapter-side-effect",
        transform(code, id) {
          if (id.includes("react-19-adapter")) {
            return {
              code,
              map: null,
              moduleSideEffects: true
            };
          }
          return null;
        }
      }
    ]
  }
});
export {
  electron_vite_config_default as default
};
