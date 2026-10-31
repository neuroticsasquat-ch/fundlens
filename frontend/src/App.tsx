import { createBrowserRouter, RouterProvider } from "react-router";
import { createQueryClient } from "./api/query";
import Providers from "./Providers";
import { routes } from "./routes";

const queryClient = createQueryClient();
const router = createBrowserRouter(routes);

function App() {
  return (
    <Providers queryClient={queryClient}>
      <RouterProvider router={router} />
    </Providers>
  );
}

export default App;
