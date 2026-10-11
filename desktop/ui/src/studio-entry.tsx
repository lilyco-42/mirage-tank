import { createRoot } from "react-dom/client";
import { MirageWorkspace } from "./mirage-workspace";
import "./studio-theme.css";

createRoot(document.getElementById("root")!).render(<MirageWorkspace />);
