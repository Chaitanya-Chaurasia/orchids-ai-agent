import Image from "next/image";
import { WaitlistForm } from "@/components/waitlist-form";

export default function CtaWithBackgroundNoise() {
  return (
    <section className="relative overflow-hidden bg-black py-20">
      <div
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          backgroundImage: "url(/noise.webp)",
          backgroundSize: "30%",
        }}
      />
      <div className="relative z-20 mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <div className="relative">
          <div
            className="pointer-events-none absolute inset-y-0 right-0 select-none overflow-hidden rounded-2xl"
            style={{
              mask: "radial-gradient(33.875rem 33.875rem at calc(100% - 8.9375rem) 0, white 3%, transparent 70%)",
            }}
          />
          <div className="relative px-6 py-10 sm:px-10 sm:pt-20 sm:pb-10 lg:px-10">
            <h2 className="text-left text-balance  text-2xl md:text-3xl lg:text-5xl font-semibold tracking-[-0.015em] text-white">
              Ready to try out the product?
            </h2>
            <p className="mt-8 max-w-[26rem] text-left  text-base/6 text-neutral-200">
              Get instant access to our state of the art project and join the
              waitlist.
            </p>

            <div className="mt-10 max-w-md">
                <WaitlistForm theme="dark" />
            </div>
          </div>
        </div>
        <div className="relative h-full flex gap-4 w-full overflow-hidden max-h-[200px] md:max-h-[400px] px-4 items-center">
          <Image
            src="https://assets.aceternity.com/pro/cta-1.jpg"
            alt="cta-1"
            width={300}
            height={500}
            className="h-full object-cover object-top rounded-lg mt-4 md:mt-0"
          />
          <Image
            src="https://assets.aceternity.com/pro/cta-2.jpg"
            alt="cta-1"
            width={300}
            height={500}
            className="h-full object-cover object-top mt-10 rounded-lg"
          />
        </div>
      </div>
    </section>
  );
}
