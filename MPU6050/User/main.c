#include "stm32f10x.h"                  // Devide header
#include "Delay.h"
#include "SI2C.h"
#include "MPU6050.h"
#include "Serial.h"
#include "LED.h"

int16_t AX,AY,AZ,GX,GY,GZ;//初始化各个轴数据变量


int main(void)
{
  MPU6050_Init();
	Serial_Init();//初始化各个模块
	LED_Init();

	MPU6050_GetData(&AX,&AY,&AZ,&GX,&GY,&GZ);
	if((AX|AY|AZ|GX|GY|GZ)!=0)//如果能正常读取数据绿灯点亮500毫秒
		{												//如果不能正常读取数据红灯点亮500毫秒
			RED_OFF();
			GREEN_ON();
		}else
		{
			GREEN_OFF();
			RED_ON();
		}
	Delay_ms(500);
	RED_OFF();
	GREEN_OFF();
		
  while (1)
  {
    MPU6050_GetData(&AX,&AY,&AZ,&GX,&GY,&GZ);								//主循环不断更新数据，用串口发送到电脑
		printf("\r\n[ACC] X=%dmg Y=%dmg Z=%dmg", AX, AY, AZ);
		printf("\r\n[GYRO] X=%ddps Y=%ddps Z=%ddps", GX, GY, GZ); 
  }
}
