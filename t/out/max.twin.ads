pragma Ada_2022;
with Ada.Numerics.Big_Numbers.Big_Integers;
use  Ada.Numerics.Big_Numbers.Big_Integers;
package T_Max with SPARK_Mode is
   function F (X : Big_Integer; Y : Big_Integer) return Big_Integer is
     (X)
   with
     Post => (F'Result >= X)
     and then (F'Result >= Y)
     and then ((F'Result = X) or else (F'Result = Y));
end T_Max;
