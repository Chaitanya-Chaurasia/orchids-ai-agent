import ThreeColumnBentoGridLight from "@/components/blocks/bento-grids/three-column-bento-grid-light";
import { CenteredWithLogo } from "@/components/blocks/footers/centered-with-logo";
import StatsForChangelog from "@/components/blocks/stats/stats-for-changelog";
import WithLargeScreenshotOnDark from "@/components/blocks/feature-sections/with-large-screenshot-on-dark";

export default function Home() {
  return (
    <main>
      <WithLargeScreenshotOnDark />
      <ThreeColumnBentoGridLight />
      <StatsForChangelog />
      <CenteredWithLogo />
    </main>
  );
}
