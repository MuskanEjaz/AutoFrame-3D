import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import RecordedDemo from "./RecordedDemo";
import "./style.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).get("workbench") === "1" ? <App /> : <RecordedDemo />}
  </React.StrictMode>,
);
