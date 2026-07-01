export const isUnder16RestrictedShift = (shift) => {
  const start = new Date(shift.start_time);
  const hour = start.getHours();

  return hour >= 20 || hour < 6;
};
