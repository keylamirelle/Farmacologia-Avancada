export type Person = {
  id: string;
  name: string;
  role: string | null;
  phone: string | null;
  active: boolean;
  created_at: string;
};

export type School = {
  id: string;
  name: string;
  city: string | null;
  active: boolean;
  created_at: string;
};

export type Material = {
  id: string;
  name: string;
  unit: string;
  total_quantity: number;
  returnable: boolean;
  created_at: string;
};

export type MaterialStatus = {
  id: string;
  name: string;
  unit: string;
  total_quantity: number;
  returnable: boolean;
  in_use: number;
  consumed: number;
  available: number;
};

export type Withdrawal = {
  id: string;
  person_id: string;
  school_id: string;
  material_id: string;
  quantity: number;
  note: string | null;
  withdrawn_at: string;
  returned_at: string | null;
};

export type WithdrawalWithJoins = Withdrawal & {
  people: Pick<Person, 'id' | 'name'> | null;
  schools: Pick<School, 'id' | 'name'> | null;
  materials: Pick<Material, 'id' | 'name' | 'unit' | 'returnable'> | null;
};
