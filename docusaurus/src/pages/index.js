import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import Heading from "@theme/Heading";

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header
      style={{
        padding: "4rem 0",
        textAlign: "center",
        backgroundColor: "var(--ifm-color-primary)",
        color: "white",
      }}
    >
      <div className="container">
        <Heading as="h1" style={{ fontSize: "3rem" }}>
          {siteConfig.title}
        </Heading>
        <p style={{ fontSize: "1.5rem", marginBottom: "2rem" }}>{siteConfig.tagline}</p>
        <Link className="button button--secondary button--lg" to="/docs/intro">
          ドキュメントを見る 📚
        </Link>
      </div>
    </header>
  );
}

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main style={{ padding: "2rem", textAlign: "center" }}>
        <p>AIエージェントが生成したドキュメントをここでプレビューできます。</p>
      </main>
    </Layout>
  );
}
