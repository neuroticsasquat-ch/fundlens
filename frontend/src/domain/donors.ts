import type { TopDonor } from "../api/client";

/** A donor's name, or their id when gold has no name for them. */
export const donorName = (donor: Pick<TopDonor, "donor_id" | "display_name">) =>
  donor.display_name ?? `Donor ${donor.donor_id}`;
