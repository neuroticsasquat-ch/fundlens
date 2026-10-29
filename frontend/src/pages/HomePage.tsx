import { buildSha } from "../config";

function HomePage() {
  return (
    <main className="shell">
      <h1>fundlens</h1>
      <p className="build">
        Build <code>{buildSha}</code>
      </p>
    </main>
  );
}

export default HomePage;
