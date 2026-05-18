export type Profile = {
  id: string;
  display_name: string | null;
  created_at: string;
};

export type Product = {
  id: string;
  name: string;
  sku: string | null;
  unit: string;
  current_stock: number;
  min_stock: number;
  created_by: string | null;
  created_at: string;
};

export type MovementType = 'entry' | 'withdrawal';

export type StockMovement = {
  id: string;
  product_id: string;
  type: MovementType;
  quantity: number;
  note: string | null;
  performed_by: string | null;
  performed_at: string;
};

export type MovementWithJoins = StockMovement & {
  products: Pick<Product, 'name' | 'unit'> | null;
  profiles: Pick<Profile, 'display_name'> | null;
};
