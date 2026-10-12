import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Workspace from "./Workspace";
import "./style.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).get("workbench") === "1" ? <App /> : <Workspace />}
  </React.StrictMode>,
);
