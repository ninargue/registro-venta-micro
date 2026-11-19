import { TextField } from "@/shared/ui/TextField";

export interface ProductSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function ProductSearchBar({ value, onChange, disabled = false }: ProductSearchBarProps) {
  return (
    <TextField
      id="catalog-search"
      label="Buscar producto"
      type="text"
      value={value}
      onChange={(e) => { onChange(e.target.value); }}
      placeholder="Buscar por nombre o SKU..."
      disabled={disabled}
    />
  );
}
