import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  companyFilters: {
    page: 1,
    page_size: 10,
    search: "",
    status: "all",
  },
  paymentFilters: {
    page: 1,
    page_size: 10,
    search: "",
    status: "all",
  },
  selectedCompanyId: null,
};

const adminSlice = createSlice({
  name: "admin",
  initialState,
  reducers: {
    setCompanyFilters(state, action) {
      state.companyFilters = { ...state.companyFilters, ...action.payload };
    },
    setPaymentFilters(state, action) {
      state.paymentFilters = { ...state.paymentFilters, ...action.payload };
    },
    setSelectedCompanyId(state, action) {
      state.selectedCompanyId = action.payload;
    },
  },
});

export const { setCompanyFilters, setPaymentFilters, setSelectedCompanyId } = adminSlice.actions;
export default adminSlice.reducer;
