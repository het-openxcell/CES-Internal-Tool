import { useCallback, useState } from "react";

import { apiClient, type OccurrenceRow } from "@/lib/api";

type EditableField = "type" | "section" | "mmd" | "density" | "notes";
type CorrectionValue = string | number | null;

const NUMERIC_FIELDS = new Set<EditableField>(["mmd", "density"]);

function parseCorrectionValue(fieldName: EditableField, correctedValue: string): CorrectionValue {
  const trimmed = correctedValue.trim();
  if (!trimmed) throw new Error("Invalid correction value");

  if (!NUMERIC_FIELDS.has(fieldName)) return trimmed;

  const value = Number(trimmed);
  if (!Number.isFinite(value)) throw new Error("Invalid correction value");
  return value;
}

export function useCorrections() {
  const [overrides, setOverrides] = useState<Record<string, Partial<OccurrenceRow>>>({});
  const [correctedIds, setCorrectedIds] = useState<Set<string>>(() => new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});

  const clearError = useCallback((occurrenceId: string) => {
    setErrors((current) => {
      const next = { ...current };
      delete next[occurrenceId];
      return next;
    });
  }, []);

  const saveCorrection = useCallback(
    async (occurrenceId: string, fieldName: EditableField, correctedValue: string, reason: string) => {
      let parsedValue: CorrectionValue;
      try {
        parsedValue = parseCorrectionValue(fieldName, correctedValue);
      } catch (error) {
        setErrors((current) => ({
          ...current,
          [occurrenceId]: error instanceof Error ? error.message : "Invalid correction value",
        }));
        throw error;
      }

      let previousOverride: Partial<OccurrenceRow> | undefined;
      let wasCorrected = false;

      setOverrides((current) => {
        previousOverride = current[occurrenceId];
        return {
          ...current,
          [occurrenceId]: { ...current[occurrenceId], [fieldName]: parsedValue },
        };
      });
      setCorrectedIds((current) => {
        wasCorrected = current.has(occurrenceId);
        return new Set(current).add(occurrenceId);
      });
      clearError(occurrenceId);

      try {
        const updatedRow = await apiClient.patchOccurrence(occurrenceId, fieldName, correctedValue, reason);
        const serverValue = updatedRow && typeof updatedRow === "object" && fieldName in updatedRow
          ? updatedRow[fieldName]
          : parsedValue;
        setOverrides((current) => ({
          ...current,
          [occurrenceId]: {
            ...current[occurrenceId],
            [fieldName]: serverValue,
          },
        }));
        return true;
      } catch (error) {
        setOverrides((current) => {
          const next = { ...current };
          const restored = { ...current[occurrenceId] } as Partial<Record<EditableField, CorrectionValue>>;
          if (previousOverride && Object.prototype.hasOwnProperty.call(previousOverride, fieldName)) {
            restored[fieldName] = previousOverride[fieldName] as CorrectionValue;
          } else {
            delete restored[fieldName];
          }
          if (Object.keys(restored).length > 0) next[occurrenceId] = restored as Partial<OccurrenceRow>;
          else delete next[occurrenceId];
          return next;
        });
        setCorrectedIds((current) => {
          const next = new Set(current);
          const keepCorrected = wasCorrected || Boolean(previousOverride && Object.keys(previousOverride).length > 0);
          if (!keepCorrected) next.delete(occurrenceId);
          return next;
        });
        setErrors((current) => ({ ...current, [occurrenceId]: "Couldn't save correction — try again" }));
        throw error;
      }
    },
    [clearError],
  );

  return { overrides, correctedIds, errors, saveCorrection, clearError };
}

export default useCorrections;
